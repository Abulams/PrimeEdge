from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

db_path = 'market_os.db'
engine = create_engine(f'sqlite:///{db_path}')

with engine.connect() as conn:
    # Get all table names
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result.fetchall()]
    
    print('=== ALL TABLES IN DATABASE ===')
    for table in tables:
        print(table)
    print()
    
    now = datetime.utcnow()
    forty_eight_hours_ago = now - timedelta(hours=48)
    
    print(f'=== ACTIVITY IN LAST 48 HOURS (since {forty_eight_hours_ago}) ===')
    
    # Check setup_snapshots
    if 'setup_snapshots' in tables:
        result = conn.execute(text('SELECT COUNT(*) FROM setup_snapshots WHERE created_at >= :cutoff'), {'cutoff': forty_eight_hours_ago})
        snapshots = result.scalar()
        print(f'Setup snapshots: {snapshots}')
    
    # Check trade_records
    if 'trade_records' in tables:
        result = conn.execute(text('SELECT COUNT(*) FROM trade_records WHERE created_at >= :cutoff'), {'cutoff': forty_eight_hours_ago})
        trades = result.scalar()
        print(f'Trade records: {trades}')
    
    # Check replay_batches
    if 'replay_batches' in tables:
        result = conn.execute(text('SELECT COUNT(*) FROM replay_batches WHERE created_at >= :cutoff'), {'cutoff': forty_eight_hours_ago})
        batches = result.scalar()
        print(f'Replay batches: {batches}')
    
    # Check trading_journal
    if 'trading_journal' in tables:
        result = conn.execute(text('SELECT COUNT(*) FROM trading_journal WHERE created_at >= :cutoff'), {'cutoff': forty_eight_hours_ago})
        journal = result.scalar()
        print(f'Trading journal entries: {journal}')
    
    # Check user logins (last_login updated in last 48h)
    result = conn.execute(text('SELECT COUNT(*) FROM users WHERE last_login >= :cutoff'), {'cutoff': forty_eight_hours_ago})
    logins = result.scalar()
    print(f'User logins (last_login updated): {logins}')
    
    # Get user details with recent activity
    result = conn.execute(text('''
        SELECT id, email, full_name, created_at, last_login, is_active
        FROM users 
        ORDER BY last_login DESC NULLS LAST
        LIMIT 10
    '''))
    
    print()
    print('=== RECENT USER ACTIVITY (Top 10 by last_login) ===')
    for user in result.fetchall():
        print(f'Email: {user[1]} | Last Login: {user[4]} | Active: {user[5]}')
