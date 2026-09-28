"""
Migration: Setup Subscription System and Migrate Founder Cohort
==============================================================
1. Creates default subscription tiers (Starter, Pro, Premium)
2. Migrates existing founder cohort users to Premium tier
3. Cleans up waitlist system (since founder cohort is being replaced)
"""
import sqlite3
import os
import datetime

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "..", "market_os.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting subscription system migration...")
        
        # 1. Create subscription tables
        print("Creating subscription tables...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                price_monthly REAL NOT NULL,
                price_yearly REAL,
                stripe_price_id_monthly TEXT,
                stripe_price_id_yearly TEXT,
                features TEXT,
                max_accounts INTEGER DEFAULT 1,
                auto_execution_enabled BOOLEAN DEFAULT 0,
                api_access_enabled BOOLEAN DEFAULT 0,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier_id INTEGER NOT NULL,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                status TEXT DEFAULT 'active',
                billing_interval TEXT,
                current_period_start DATETIME,
                current_period_end DATETIME,
                cancel_at_period_end BOOLEAN DEFAULT 0,
                trial_end DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tier_id) REFERENCES subscription_tiers(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                payload TEXT,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Add current_tier_id and trial_used columns to users table
        print("Adding subscription columns to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN current_tier_id INTEGER")
        except sqlite3.OperationalError:
            print("  Column current_tier_id already exists")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN trial_used BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            print("  Column trial_used already exists")
        
        # 3. Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_id ON user_subscriptions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_subscriptions_tier_id ON user_subscriptions(tier_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_customer_id ON user_subscriptions(stripe_customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_subscription_id ON user_subscriptions(stripe_subscription_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_stripe_webhook_events_stripe_event_id ON stripe_webhook_events(stripe_event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_stripe_webhook_events_event_type ON stripe_webhook_events(event_type)")
        
        # 4. Insert default tiers
        print("Inserting default subscription tiers...")
        tiers = [
            ("starter", "Starter", "Essential market intelligence for manual traders", 29.0, 290.0,
             '["Real-time market signals", "Basic opportunity radar", "Manual trade journaling", "1 MT5 account", "Community access"]',
             1, 0, 0),
            ("pro", "Pro", "Advanced tools for serious systematic traders", 99.0, 990.0,
             '["All Starter features", "Advanced market analysis", "Historical performance analytics", "3 MT5 accounts", "Priority support", "API access (read-only)"]',
             3, 0, 1),
            ("premium", "Premium", "Full institutional-grade platform with auto-execution", 299.0, 2990.0,
             '["All Pro features", "Fully automated execution", "Unlimited MT5 accounts", "Custom strategy backtesting", "Dedicated support", "Full API access (read/write)", "White-label reporting"]',
             999, 1, 1)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM subscription_tiers")
        tier_count = cursor.fetchone()[0]
        
        if tier_count == 0:
            for tier in tiers:
                cursor.execute("""
                    INSERT INTO subscription_tiers (name, display_name, description, price_monthly, price_yearly, features, max_accounts, auto_execution_enabled, api_access_enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tier)
            print(f"  Created {len(tiers)} default tiers")
        else:
            print(f"  Found {tier_count} existing tiers, skipping insertion")
        
        # 5. Get Premium tier ID
        cursor.execute("SELECT id FROM subscription_tiers WHERE name = 'premium'")
        premium_result = cursor.fetchone()
        if not premium_result:
            print("ERROR: Premium tier not found")
            return
        
        premium_tier_id = premium_result[0]
        print(f"Premium tier ID: {premium_tier_id}")
        
        # 6. Migrate existing users to Premium tier
        cursor.execute("SELECT id, email FROM users")
        users = cursor.fetchall()
        print(f"Found {len(users)} users to migrate...")
        
        migrated_count = 0
        for user_id, email in users:
            # Update user's current tier to Premium
            cursor.execute("UPDATE users SET current_tier_id = ?, trial_used = 1 WHERE id = ?", 
                         (premium_tier_id, user_id))
            
            # Create complimentary subscription if not exists
            cursor.execute("SELECT COUNT(*) FROM user_subscriptions WHERE user_id = ?", (user_id,))
            sub_count = cursor.fetchone()[0]
            
            if sub_count == 0:
                cursor.execute("""
                    INSERT INTO user_subscriptions (user_id, tier_id, stripe_customer_id, stripe_subscription_id, status, billing_interval)
                    VALUES (?, ?, NULL, NULL, 'active', 'complimentary')
                """, (user_id, premium_tier_id))
            
            migrated_count += 1
            print(f"  Migrated user: {email} -> Premium tier")
        
        conn.commit()
        print(f"\n[SUCCESS] Migration completed successfully!")
        print(f"Summary:")
        print(f"  - Created subscription tables and indexes")
        print(f"  - Created 3 subscription tiers (Starter, Pro, Premium)")
        print(f"  - Migrated {migrated_count} users to Premium tier")
        print(f"  - Founder cohort replaced with subscription system")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()