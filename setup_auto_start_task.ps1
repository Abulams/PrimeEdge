# Market-OS Windows Auto-Start & Persistence Task Installer
# Configures a Windows Scheduled Task to run watchdog.py at system startup and logon

$TaskName = "MarketOS_Persistence_Supervisor"
$PythonPath = "C:\Python311\python.exe"
$WatchdogPath = "C:\Market-OS\watchdog.py"

Write-Output "Configuring 24/7 Persistence Task: $TaskName..."

# Unregister if previously exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Define action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $WatchdogPath -WorkingDirectory "C:\Market-OS"

# Define triggers (At Startup + At User Logon)
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Define settings (Restart on failure, run indefinitely)
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

# Define principal (Run with highest privileges)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# Register task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger @($TriggerStartup, $TriggerLogon) `
    -Settings $Settings `
    -Principal $Principal `
    -Description "24/7 Self-Healing Supervisor for Market-OS Backend, MT5, and Execution Engine." | Out-Null

Write-Output "✅ Scheduled Task '$TaskName' registered successfully."
Write-Output "Market-OS will now automatically launch on boot and stay alive 24/7."
