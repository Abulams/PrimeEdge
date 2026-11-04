import paramiko
from scp import SCPClient
import time
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

VPS_HOST = '172.237.112.138'
VPS_USER = 'root'
VPS_PASS = 'AbubakarLamido556@'
VPS_APP_PATH = '/opt/market-os'
VENV_PIP = '/opt/market-os/backend/venv/bin/pip'

LOCAL_BASE = r'C:\Users\qsoft\Downloads\Market-OS-Recovered\Market-OS\backend\app'

FILES = [
    (
        LOCAL_BASE + r'\execution\ctrader_copier_service.py',
        VPS_APP_PATH + '/backend/app/execution/ctrader_copier_service.py'
    ),
    (
        LOCAL_BASE + r'\analyst_engine.py',
        VPS_APP_PATH + '/backend/app/analyst_engine.py'
    ),
    (
        LOCAL_BASE + r'\telegram_service.py',
        VPS_APP_PATH + '/backend/app/telegram_service.py'
    ),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting...")
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
print("Connected!")

def run(cmd, label=''):
    stdin, stdout, stderr = ssh.exec_command(cmd + ' 2>&1')
    stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    if label:
        print(f"[{label}] {out[:600] if out else 'OK'}")
    return out

# Verify which files were actually uploaded (check sizes / timestamps)
print("\n=== Verifying uploaded files ===")
for _, remote in FILES:
    fname = remote.split('/')[-1]
    run(f'ls -la {remote} {remote}.bak 2>&1', f'check {fname}')

# Upload any that are missing (in case first upload failed)
print("\n=== Uploading files ===")
with SCPClient(ssh.get_transport()) as scp:
    for local, remote in FILES:
        fname = local.split('\\')[-1]
        print(f"  Uploading {fname}...")
        scp.put(local, remote)
        print(f"  DONE: {fname}")

print("\n=== Verifying upload sizes ===")
for _, remote in FILES:
    fname = remote.split('/')[-1]
    run(f'wc -l {remote}', f'lines in {fname}')

# Install certifi into the venv
print("\n=== Installing certifi into venv ===")
run(f'{VENV_PIP} install certifi --quiet', 'certifi install')
run(f'{VENV_PIP} show certifi', 'certifi version')

# Restart all 3 services
print("\n=== Restarting services ===")
for svc in ['marketos-backend', 'ctrader-copier', 'sia-telegram-hub']:
    out = run(f'systemctl restart {svc}')
    print(f"  restart {svc}: {out if out else 'OK'}")

time.sleep(5)

# Final status
print("\n=== Service status ===")
print(run('systemctl is-active marketos-backend ctrader-copier sia-telegram-hub'))

# Recent logs
print("\n=== marketos-backend logs (last 25 lines) ===")
print(run('journalctl -u marketos-backend -n 25 --no-pager'))

print("\n=== sia-telegram-hub logs (last 15 lines) ===")
print(run('journalctl -u sia-telegram-hub -n 15 --no-pager'))

# Test health endpoint
print("\n=== Health check via curl ===")
print(run('curl -s http://localhost:8000/api/v1/health 2>&1 | head -5'))

ssh.close()
print("\n=== DEPLOYMENT COMPLETE ===")
