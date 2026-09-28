"""
Migration: Add trade_id foreign key to ExecutionAuditLog
This enables complete traceability from execution audit logs to journal trade records.
"""
import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "..", "market_os.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(execution_audit_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'trade_id' in columns:
            print("Column 'trade_id' already exists in execution_audit_logs table.")
            return
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE execution_audit_logs 
            ADD COLUMN trade_id INTEGER
        """)
        
        # Create index for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_execution_audit_logs_trade_id 
            ON execution_audit_logs(trade_id)
        """)
        
        conn.commit()
        print("Successfully added 'trade_id' column to execution_audit_logs table.")
        print("Created index ix_execution_audit_logs_trade_id for performance.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()