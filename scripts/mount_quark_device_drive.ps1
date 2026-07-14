$ErrorActionPreference = 'Stop'

# Explorer fixed drives are per-user. This script is launched by the user logon task.
$drive = 'X:'
$driveConfig = Join-Path $env:USERPROFILE 'DiskCleaner_quark_drive.json'
if (Test-Path $driveConfig) {
    try {
        $configuredDrive = (Get-Content -LiteralPath $driveConfig -Raw | ConvertFrom-Json).drive
        if ($configuredDrive -match '^[D-Zd-z]:$') {
            $drive = $configuredDrive.ToUpper()
        }
    }
    catch {
        # A missing or invalid preference must not prevent the default X: mount.
    }
}
$driveLetter = $drive.TrimEnd(':')
$projectRoot = Split-Path -Parent $PSScriptRoot
# Use Windows' native transparent fixed-disk resource. Do not use an icon
# extracted from Explorer: it turns transparent pixels into a black square.
$fixedDriveIcon = "$env:SystemRoot\System32\imageres.dll,-36"
foreach ($iconKey in @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\$driveLetter\DefaultIcon",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\DriveIcons\$driveLetter\DefaultIcon"
)) {
    try {
        New-Item -Path $iconKey -Force | Out-Null
        Set-ItemProperty -Path $iconKey -Name '(default)' -Value $fixedDriveIcon
    }
    catch {
        # A standard-user session may not change HKLM; its HKCU entry is enough.
    }
}
# Refresh the shell's icon association without restarting Explorer.
Start-Process -FilePath "$env:SystemRoot\System32\ie4uinit.exe" -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue
$volumeName = -join ([char]0x5938, [char]0x514B, [char]0x7F51, [char]0x76D8)

if (Test-Path "$drive\") {
    exit 0
}

$rclone = Get-Command 'rclone.exe' -ErrorAction SilentlyContinue
if (-not $rclone) {
    exit 1
}

# AList 2.x on this computer does not support the Quark storage driver.
# Start the local Quark-backed WebDAV bridge instead. It only listens on
# 127.0.0.1, and rclone exposes it to Explorer as a fixed drive.
$cookies = Join-Path $projectRoot 'quark_mount_cookies.json'
$server = Join-Path $PSScriptRoot 'quark_webdav_server.py'
$log = Join-Path $projectRoot 'data\quark_webdav.log'
$logDirectory = Split-Path -Parent $log
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$python = Get-Command 'python.exe' -ErrorAction SilentlyContinue
if (-not (Test-Path $cookies) -or -not (Test-Path $server) -or -not $python) {
    exit 2
}

if (-not (Test-NetConnection -ComputerName '127.0.0.1' -Port 5245 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    $bridgeArguments = '"{0}" --cookies "{1}" --port 5245 --log "{2}"' -f $server, $cookies, $log
    Start-Process -FilePath $python.Source -WindowStyle Hidden -ArgumentList @(
        $bridgeArguments
    )
}

for ($attempt = 0; $attempt -lt 18; $attempt++) {
    if (Test-NetConnection -ComputerName '127.0.0.1' -Port 5245 -InformationLevel Quiet -WarningAction SilentlyContinue) {
        break
    }
    Start-Sleep -Seconds 5
}

Start-Process -FilePath $rclone.Source -WindowStyle Hidden -ArgumentList @(
    'mount', 'quark-device:', $drive,
    '--vfs-cache-mode', 'writes',
    '--dir-cache-time', '1m',
    '--volname', $volumeName,
    '--no-console'
)

# AList and the Quark backend can come up after Windows. Keep the launcher
# alive long enough for WinFsp/rclone to expose the device drive to Explorer.
for ($attempt = 0; $attempt -lt 18; $attempt++) {
    Start-Sleep -Seconds 5
    if (Test-Path "$drive\") {
        exit 0
    }
}

exit 2
