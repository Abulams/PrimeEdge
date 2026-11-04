import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Attempting SSH connection to 172.237.112.138...")
    ssh.connect('172.237.112.138', username='root', password='AbubakarLamido556@', timeout=15)
    print('SSH CONNECTED!')
    stdin, stdout, stderr = ssh.exec_command('whoami && uptime')
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("STDERR:", err)
    
    # Check service status
    stdin2, stdout2, stderr2 = ssh.exec_command('systemctl list-units --type=service --state=running | grep -i -E "market|prime|gunicorn|uvicorn|fastapi" 2>&1')
    svc = stdout2.read().decode()
    print("Services:", svc if svc else "(none matching)")
    
    # Check what's listening on 8000
    stdin3, stdout3, stderr3 = ssh.exec_command('ss -tlnp | grep -E "8000|8080|80" 2>&1')
    print("Ports:", stdout3.read().decode())
    
    ssh.close()
except Exception as e:
    print(f'FAILED: {type(e).__name__}: {e}')
