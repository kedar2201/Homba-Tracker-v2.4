# deploy_to_server.ps1
# This script deploys the Portfolio Tracker application to the remote Windows Server.

$RemoteIP = "103.255.191.35"
$RemoteUser = "win_admin"
$RemotePath = "C:\apps\portfolio"
$SSH = "C:\Windows\System32\OpenSSH\ssh.exe"
$SCP = "C:\Windows\System32\OpenSSH\scp.exe"
$PM2Name = "portfolio-backend"

Write-Host "--- 🏗️ Preparing Deployment Packages ---" -ForegroundColor Cyan

# 1. Zip Backend (Excluding DB and cache)
Write-Host "Zipping backend (excluding .db files)..."
$BackendZip = "backend_update.zip"
Remove-Item $BackendZip -ErrorAction SilentlyContinue

# We'll copy to a temp folder first to exclude files easily
$TempBackend = "tmp_backend_deploy"
if (Test-Path $TempBackend) { Remove-Item $TempBackend -Recurse -Force }
New-Item -ItemType Directory -Path $TempBackend

Copy-Item "backend\*" -Destination $TempBackend -Recurse -Exclude "*.db", "*.sqlite", "__pycache__", "*.log"
Compress-Archive -Path "$TempBackend\*" -DestinationPath $BackendZip -Force
Remove-Item $TempBackend -Recurse -Force

# 2. Zip Frontend Dist
Write-Host "Zipping frontend..."
$FrontendZip = "frontend_update.zip"
Remove-Item $FrontendZip -ErrorAction SilentlyContinue
Compress-Archive -Path "frontend\dist\*" -DestinationPath $FrontendZip -Force

Write-Host "--- 🚚 Uploading to Server ---" -ForegroundColor Cyan
Write-Host "Target: $RemoteUser@$RemoteIP"

& $SCP $BackendZip "$RemoteUser@$RemoteIP:$RemotePath\backend_update.zip"
& $SCP $FrontendZip "$RemoteUser@$RemoteIP:$RemotePath\frontend_update.zip"

Write-Host "--- 🚀 Executing Remote Deploy ---" -ForegroundColor Cyan

$RemoteCommands = @"
cd /d $RemotePath

Write-Host '--- 📦 Creating Backup ---'
if (Test-Path 'backend_old') { Remove-Item 'backend_old' -Recurse -Force }
Move-Item 'backend' 'backend_old' -Force
New-Item -ItemType Directory -Path 'backend' -Force

Write-Host '--- 🛑 Stopping Service: $PM2Name ---'
pm2 stop $PM2Name

Write-Host '--- 📂 Extracting Packages ---'
powershell -Command "Expand-Archive -Path backend_update.zip -DestinationPath backend -Force"
powershell -Command "Expand-Archive -Path frontend_update.zip -DestinationPath . -Force"

Write-Host '--- 📂 Restoring Database ---'
if (Test-Path 'backend_old\portfolio.db') {
    Copy-Item 'backend_old\portfolio.db' 'backend\portfolio.db' -Force
}

Write-Host '--- 🐍 Updating Dependencies ---'
cd backend
python -m pip install -r requirements.txt

Write-Host '--- 🚀 Restarting Service: $PM2Name ---'
pm2 start $PM2Name

Write-Host '--- ✅ DEPLOYMENT FINISHED ---'
"@

# We run these via SSH
& $SSH "$RemoteUser@$RemoteIP" "powershell -Command `$RemoteCommands`"

Write-Host "Done!" -ForegroundColor Green
