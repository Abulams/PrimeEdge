import paramiko

VPS_HOST = '172.237.112.138'
VPS_USER = 'root'
VPS_PASS = 'AbubakarLamido556@'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=15)
print("Connected!")

# Find where the app lives
cmds = [
    "find / -name 'analyst_engine.py' 2>/dev/null",
    "find / -name 'telegram_service.py' 2>/dev/null",
    "find / -name 'main.py' -path '*/market*' 2>/dev/null",
    "find / -name 'main.py' -path '*/prime*' 2>/dev/null",
    "cat /etc/systemd/system/marketos-backend.service",
    "cat /etc/systemd/system/ctrader-copier.service",
    "cat /etc/systemd/system/sia-telegram-hub.service",
    "ls /var/www/ 2>/dev/null || echo 'no /var/www'",
    "ls /opt/ 2>/dev/null",
    "ls /home/ 2>/dev/null",
]

for cmd in cmds:
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd + ' 2>&1')
    stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    print(out[:1000] if len(out) > 1000 else out)

ssh.close()
