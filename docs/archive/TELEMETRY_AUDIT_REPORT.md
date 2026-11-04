# Market OS Telemetry Cross-Contamination Audit Report
## September 2, 2026

### Critical Issues Identified

## Issue 1: Telemetry Cross-Contamination (Account Balances & Latencies Bleeding)

### **Root Cause Analysis**

**Location**: `worker/marketos_worker.py` - `send_heartbeat()` function (lines 517-564)

**Problem**: The heartbeat loop reads account information without proper isolation between user accounts.

```python
def send_heartbeat(accounts: List[Dict]):
    t_statuses = {}
    for acc in accounts:
        acc_id = acc["account_id"]
        login = acc["login"]
        connected = False
        balance = 0.0
        equity = 0.0
        ping_ms = 0.0

        with _mt5_lock:
            if MT5_AVAILABLE:
                try:
                    if ensure_connected_to_account(login, acc["password"], acc.get("server", "MetaQuotes-Demo")):
                        ai = mt5.account_info()  # ❌ PROBLEM: Reads whatever account is active
                        ti = mt5.terminal_info()
                        if ai:
                            connected = True
                            balance = float(ai.balance)  # ❌ CROSS-CONTAMINATION
                            equity = float(ai.equity)
                            ping_ms = float(getattr(ti, "ping_last", 3500) / 1000.0) if ti else 3.5
                except Exception:
                    pass

        t_statuses[str(acc_id)] = {
            "status": "CONNECTED" if connected else "SANDBOX",
            "ping_ms": round(ping_ms, 2),
            "balance": balance,  # ❌ WRONG ACCOUNT DATA
            "equity": equity
        }
```

**The Problem**: 
- `ensure_connected_to_account()` calls `mt5.login()` to switch accounts
- If login fails or is slow, the terminal remains connected to the previous account
- `mt5.account_info()` then reads the wrong account's data
- No validation that the account info matches the requested login

**Evidence from Screenshots**:
- Screenshot 1: abu1@gmail.com (111729335) and lamido665@gmail.com (5054957055) show identical balance ($110,848.22) and latency (286.7ms)
- Screenshot 2: abu1@gmail.com (111729335) swapped balances with adamswakeeli@gmail.com (10012394906) — both showing $97,155.23

**Vulnerability**: In single-terminal worker, when `mt5.login()` switches between accounts during heartbeat loop, if account switch fails or is queried concurrently, `mt5.account_info()` reads the active terminal session of the other account instead of isolating each subscriber's data.

---

## Issue 2: High VPS Resource Utilization

### **Root Cause Analysis**

**Location**: `worker/marketos_worker.py` - Main loop (lines 571-634)

**Problem**: Aggressive polling frequency causing CPU pinning

```python
while True:
    try:
        # Refresh account list every 30 cycles (~90s)
        if cycle % 30 == 0:
            fresh = get_accounts()
            if fresh:
                accounts = fresh
                # ... terminal initialization

        # Poll and execute pending orders
        if accounts:
            poll_and_execute_orders(accounts)

        # Sync positions and check early invalidation for each account
        for acc in accounts:
            sync_positions_to_cloud(acc_id, login, password, server)
            check_local_invalidation(acc_id, login, password, server)

        # Send heartbeat every 2 cycles (~6-10s)
        if cycle % 2 == 0 and accounts:
            send_heartbeat(accounts)

        cycle += 1
        time.sleep(3)  # ❌ AGGRESSIVE POLLING
```

**The Problem**:
- 3-second sleep interval in main loop
- Multiple MT5 API calls per cycle per account
- Position sync, early invalidation check, and heartbeat all call MT5 APIs
- No backoff when operations fail
- Tight retry attempts when switching terminal accounts

**Evidence from Screenshots**:
- CPU: Pinned at 100% in both screenshots
- RAM: High at 87% – 89.7%

**Calculation**: With 3 accounts, main loop performs:
- Order polling every 3 seconds
- Position sync for each account every 3 seconds  
- Early invalidation check for each account every 3 seconds
- Heartbeat every 6 seconds
- MT5 login attempts potentially every 3 seconds

**Result**: ~15-20 MT5 API calls per 3-second cycle = 300-400 calls per minute

---

## Issue 3: Account #2 Flapping Between Real & Sandbox

### **Root Cause Analysis**

**Location**: `worker/marketos_worker.py` - `ensure_connected_to_account()` (lines 95-111)

**Problem**: Failed account switches cause fallback to simulation mode

```python
def ensure_connected_to_account(login: int, password: str, server: str) -> bool:
    """Ensure MT5 is connected to the correct account."""
    if not MT5_AVAILABLE:
        return False
    try:
        acc = mt5.account_info()
        if acc and acc.login == login:
            return True
        # Switch account
        ok = mt5.login(login, password=password, server=server)  # ❌ CAN FAIL
        if ok:
            return True
        # Cold reinitialize
        return initialize_terminal(login, password, server)  # ❌ CAN FAIL
    except Exception as e:
        logger.error(f"ensure_connected error for {login}: {e}")
        return False  # ❌ RETURNS FALSE
```

**The Problem**:
- When `mt5.login()` fails, function returns `False`
- Heartbeat interprets `False` as "SANDBOX" status
- No retry logic or exponential backoff
- No persistent state tracking of connection failures

**Evidence from Screenshots**:
- Screenshot 1: lamido665@gmail.com shows LIVE MT5 BROKER (inherited Account #1's session state)
- Screenshot 2: Fell back to SANDBOX SIMULATION (10000.0ms latency / Eq: $0.00) when account switch failed

**Vulnerability**: Failed account switches are not retried or handled gracefully, causing flapping between live and sandbox states.

---

## Architectural Issues

### 1. Missing Account Isolation

**Current Architecture**: Single terminal + account cycling
- All accounts share one MT5 terminal session
- No per-account state isolation
- MT5 API calls are not account-scoped

**Impact**: Any MT5 API failure affects all accounts' telemetry

### 2. Synchronous MT5 Operations

**Current Design**: All MT5 operations are synchronous and blocking
- `mt5.login()` blocks until completion
- `mt5.account_info()` blocks until completion
- No async operations or timeouts

**Impact**: Slow operations cascade across all accounts

### 3. No Account State Validation

**Current Design**: No validation that MT5 account matches requested account
- No check that `mt5.account_info().login == requested_login`
- No fallback when data doesn't match expectations
- No error reporting for cross-contamination

**Impact**: Silent data leakage between accounts

---

## Security & Privacy Implications

### Critical Vulnerability

**Cross-User Data Exposure**: User A can see User B's account balance, equity, and trading positions
- Account balances bleeding between users
- Trading positions potentially visible to wrong users
- Latency data from wrong accounts

**Privacy Violation**: User financial data exposed to other users
- Account balances
- Equity information  
- Trading performance data

---

## Recommended Fixes

### Priority 1: Account Isolation Fix

**Solution**: Add account validation to prevent cross-contamination

```python
def ensure_connected_to_account(login: int, password: str, server: str) -> bool:
    """Ensure MT5 is connected to the correct account with validation."""
    if not MT5_AVAILABLE:
        return False
    try:
        acc = mt5.account_info()
        if acc and acc.login == login:
            return True  # Already connected to correct account
        
        # Switch account
        ok = mt5.login(login, password=password, server=server)
        if ok:
            # Validate the switch was successful
            acc = mt5.account_info()
            if acc and acc.login == login:
                return True  # Switch successful and validated
            else:
                logger.error(f"Login succeeded but wrong account returned: {acc.login if acc else 'None'}")
                return False  # ❌ DATA CONTAMINATION PREVENTED
        
        # Cold reinitialize with validation
        ok = initialize_terminal(login, password, server)
        if ok:
            acc = mt5.account_info()
            if acc and acc.login == login:
                return True
            else:
                logger.error(f"Initialize succeeded but wrong account: {acc.login if acc else 'None'}")
                return False
        
        return False
    except Exception as e:
        logger.error(f"ensure_connected error for {login}: {e}")
        return False
```

### Priority 2: CPU Optimization

**Solution**: Reduce polling frequency and add backoff

```python
# Increase main loop sleep time
time.sleep(10)  # Instead of time.sleep(3)

# Reduce heartbeat frequency
if cycle % 10 == 0 and accounts:  # Instead of cycle % 2
    send_heartbeat(accounts)

# Add exponential backoff for failed operations
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
```

### Priority 3: Connection State Management

**Solution**: Add retry logic and connection state tracking

```python
# Add connection state tracking
_connection_state = {
    login: {
        "last_success": None,
        "consecutive_failures": 0,
        "last_validated_balance": None
    }
    for acc in accounts
}

# Add retry logic with exponential backoff
for attempt in range(MAX_RETRIES):
    ok = mt5.login(login, password=password, server=server)
    if ok:
        _connection_state[login]["consecutive_failures"] = 0
        _connection_state[login]["last_success"] = datetime.datetime.utcnow()
        break
    else:
        _connection_state[login]["consecutive_failures"] += 1
        time.sleep(RETRY_DELAY * (2 ** attempt))
```

### Priority 4: Per-Account Terminal Sessions

**Long-term Solution**: Consider separate MT5 terminal instances per account
- Prevents cross-contamination at architectural level
- Increases resource requirements but improves isolation
- Can be implemented with Docker containers

---

## Testing Recommendations

### Immediate Tests

1. **Account Isolation Test**: Switch between accounts and verify account_info() returns correct data
2. **CPU Profiling**: Profile worker CPU usage during account switching
3. **Connection Failure Test**: Simulate login failures and verify fallback behavior
4. **Concurrent Access Test**: Simulate concurrent heartbeat and order execution

### Monitoring Additions

1. **Account Validation Log**: Log when account validation fails
2. **Cross-Contamination Detection**: Alert when consecutive accounts show identical data
3. **CPU Usage Alert**: Alert when CPU exceeds 80% for extended periods
4. **Connection State Tracking**: Monitor login success/failure rates per account

---

## Severity Assessment

### Critical Severity
- **Account Isolation Failure**: Security vulnerability exposing user financial data
- **Cross-Contamination**: Privacy violation between users

### High Severity  
- **CPU Pinning**: System performance degradation
- **Connection Flapping**: Unreliable service state

### Medium Severity
- **Resource Utilization**: High RAM usage but not critical
- **Polling Frequency**: Inefficient but not security-critical

---

## Implementation Priority

### Immediate (This Week)
1. Add account validation to `ensure_connected_to_account()`
2. Add cross-contamination detection logging
3. Reduce polling frequency to prevent CPU pinning

### Short-term (This Month)
1. Implement retry logic with exponential backoff
2. Add connection state tracking
3. Implement CPU usage monitoring and alerts

### Long-term (Next Quarter)
1. Evaluate per-account terminal sessions
2. Consider architectural redesign for better isolation
3. Implement async MT5 operations

---

## Conclusion

The telemetry cross-contamination issue is a **critical security vulnerability** that requires immediate attention. The root cause is insufficient account isolation in the single-terminal multi-account architecture, combined with aggressive polling that causes CPU pinning.

The recommended fixes focus on account validation, reduced polling frequency, and improved connection state management. The long-term solution may involve architectural changes to improve account isolation.

**V4 MT5 connector needs immediate fixes before any additional features are added.**