[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -Path 'C:\Temp' -ItemType Directory -Force -ErrorAction SilentlyContinue

Write-Output "Downloading official Python 3.11.9..."
(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', 'C:\Temp\python-3.11.9.exe')

$size = (Get-Item 'C:\Temp\python-3.11.9.exe').Length
Write-Output "Downloaded installer size: $size bytes"

Write-Output "Running silent installer..."
$proc = Start-Process -FilePath "C:\Temp\python-3.11.9.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_lib=1 Include_test=0" -PassThru -Wait
Write-Output "Installer exit code: $($proc.ExitCode)"

Write-Output "Searching for installed python.exe:"
$py = Get-ChildItem -Path "C:\Program Files\Python*","C:\Python*","C:\Users\*\AppData\Local\Programs\Python\*" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
Write-Output "Found Python at: $py"

if ($py) {
    Write-Output "Testing Python:"
    & $py[0] --version
    
    Write-Output "Creating virtual environment in C:\Market-OS\backend\venv..."
    cd C:\Market-OS\backend
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue venv
    & $py[0] -m venv venv
    
    Write-Output "Installing pip packages..."
    .\venv\Scripts\pip.exe install --upgrade pip
    .\venv\Scripts\pip.exe install -r requirements.txt
    .\venv\Scripts\pip.exe install MetaTrader5
    
    Write-Output "Starting Market OS Server & MT5 Worker..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Market-OS\backend; .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Market-OS\backend; .\venv\Scripts\python.exe mt5_worker.py"
    
    Write-Output "MARKET_OS_FULLY_STARTED_SUCCESSFULLY"
}
