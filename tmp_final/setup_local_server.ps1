# setup_local_server.ps1
# Run as Administrator on the Local Server

$InstallPath = "C:\apps\portfolio"
$SiteName = "PortfolioTracker"
$BackendPort = 8000

# 1. Create Directory Structure
Write-Host "--- 🏗️ Setting up directory structure ---" -ForegroundColor Cyan
if (!(Test-Path $InstallPath)) { 
    New-Item -ItemType Directory -Path $InstallPath -Force 
}
if (!(Test-Path "$InstallPath\frontend")) { 
    New-Item -ItemType Directory -Path "$InstallPath\frontend" -Force 
}

# 2. Check Prerequisites
Write-Host "--- 🔍 Checking IIS & PM2 ---" -ForegroundColor Cyan
if (!(Get-Module -ListAvailable WebAdministration)) { 
    Write-Error "IIS is not installed. Please install IIS first."
    exit
}

# 3. Setup Python Backend
Write-Host "--- 🐍 Setting up Python Backend ---" -ForegroundColor Cyan
if (Test-Path "$InstallPath\backend") {
    Set-Location "$InstallPath\backend"
    # Try to find python
    $PyPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (!$PyPath) { $PyPath = "python" }
    
    & $PyPath -m pip install -r requirements.txt
} else {
    Write-Warning "Backend folder not found at $InstallPath\backend"
}

# Create the startup batch file (matches Cloud exactly)
$BatContent = @"
cd /d $InstallPath\backend
uvicorn main:app --host 0.0.0.0 --port $BackendPort
"@
$BatContent | Out-File -FilePath "$InstallPath\backend\start_portfolio.bat" -Encoding ASCII

# 4. Configure IIS Website
Write-Host "--- 🌐 Configuring IIS Website ---" -ForegroundColor Cyan
Import-Module WebAdministration

if (Get-Website -Name $SiteName) {
    Write-Host "Removing existing website $SiteName..."
    Remove-Website -Name $SiteName
}

# Point to the frontend folder
New-Website -Name $SiteName -Port 80 -PhysicalPath "$InstallPath\frontend" -Force

# 5. Configure Reverse Proxy (URL Rewrite)
Write-Host "--- 🔄 Setting up Reverse Proxy ---" -ForegroundColor Cyan
$WebConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="Reverse Proxy to API" stopProcessing="true">
                    <match url="api/(.*)" />
                    <action type="Rewrite" url="http://127.0.0.1:$BackendPort/api/{R:1}" />
                </rule>
                <rule name="React Routes" stopProcessing="false">
                    <match url=".*" />
                    <conditions logicalGrouping="MatchAll">
                        <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
                        <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
                    </conditions>
                    <action type="Rewrite" url="index.html" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
"@
$WebConfig | Out-File -FilePath "$InstallPath\frontend\web.config" -Encoding UTF8

# 6. Start with PM2
Write-Host "--- 🚀 Launching API with PM2 ---" -ForegroundColor Cyan
& pm2 delete $SiteName-api 2>$null
& pm2 start "$InstallPath\backend\start_portfolio.bat" --name "$SiteName-api"
& pm2 save

Write-Host "--- ✅ REPLICATION COMPLETE! ---" -ForegroundColor Green
Write-Host "Local Server is now running at: http://localhost"
