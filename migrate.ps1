# migrate.ps1
Write-Host "Starting migration from Ares to Ares..." -ForegroundColor Cyan

# 1. Stop any running processes from the ares directory
Write-Host "Stopping any running Ares processes..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.Path -like "C:\Users\krish\AppData\Local\ares\*" } | ForEach-Object {
    Write-Host "Stopping process: $($_.Name) ($($_.Id))" -ForegroundColor Magenta
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# 2. Rename the directory
Write-Host "Renaming directory C:\Users\krish\AppData\Local\ares to C:\Users\krish\AppData\Local\ares..." -ForegroundColor Yellow
if (Test-Path "C:\Users\krish\AppData\Local\ares") {
    Rename-Item -Path "C:\Users\krish\AppData\Local\ares" -NewName "ares" -Force
} else {
    Write-Host "Source directory C:\Users\krish\AppData\Local\ares not found. Checking if already renamed..." -ForegroundColor Red
}

if (-not (Test-Path "C:\Users\krish\AppData\Local\ares")) {
    Write-Error "Migration failed: Destination directory C:\Users\krish\AppData\Local\ares does not exist."
    exit 1
}

# 3. Update environment variables in the user registry
Write-Host "Updating registry environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("ARES_HOME", "C:\Users\krish\AppData\Local\ares", "User")
[Environment]::SetEnvironmentVariable("ARES_HOME", "C:\Users\krish\AppData\Local\ares", "User")
[Environment]::SetEnvironmentVariable("ARES_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
# Set in current session too
$env:ARES_HOME = "C:\Users\krish\AppData\Local\ares"
$env:ARES_HOME = "C:\Users\krish\AppData\Local\ares"
$env:ARES_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"

# 4. Process files in the renamed directory
$aresDir = "C:\Users\krish\AppData\Local\ares"

# A. Rename and update Ares_Gateway.cmd
$oldGateway = Join-Path $aresDir "gateway-service\Ares_Gateway.cmd"
$newGateway = Join-Path $aresDir "gateway-service\Ares_Gateway.cmd"
if (Test-Path $oldGateway) {
    Write-Host "Updating gateway command script..." -ForegroundColor Yellow
    $content = Get-Content $oldGateway
    $content = $content -replace "C:\\Users\\krish\\AppData\\Local\\ares", "C:\Users\krish\AppData\Local\ares"
    $content = $content -replace "ARES_HOME", "ARES_HOME"
    $content = $content -replace "ARES_GATEWAY_DETACHED", "ARES_GATEWAY_DETACHED"
    
    # insert ARES_HOME fallback just in case
    $newContent = @()
    foreach ($line in $content) {
        $newContent += $line
        if ($line -like '*set "ARES_HOME=*') {
            $newContent += 'set "ARES_HOME=C:\Users\krish\AppData\Local\ares"'
        }
        if ($line -like '*set "ARES_GATEWAY_DETACHED=*') {
            $newContent += 'set "ARES_GATEWAY_DETACHED=1"'
        }
    }
    $newContent | Set-Content $newGateway
    Remove-Item $oldGateway -Force
}

# B. Update pyvenv.cfg
$pyvenvCfg = Join-Path $aresDir "ares-agent\venv\pyvenv.cfg"
if (Test-Path $pyvenvCfg) {
    Write-Host "Updating pyvenv.cfg..." -ForegroundColor Yellow
    $content = Get-Content $pyvenvCfg
    $content = $content -replace "C:\\Users\\krish\\AppData\\Local\\ares", "C:\Users\krish\AppData\Local\ares"
    $content | Set-Content $pyvenvCfg
}

# C. Recursively update text files in the new ares folder (excluding large libraries and binaries)
Write-Host "Updating text files in C:\Users\krish\AppData\Local\ares..." -ForegroundColor Yellow
$excludePatterns = @('*\.git\*', '*\node_modules\*', '*\venv\Lib\*', '*\__pycache__\*', '*\cache\*', '*\logs\*', '*\.docker\*')
Get-ChildItem -Path $aresDir -Recurse -File | ForEach-Object {
    $file = $_.FullName
    
    $exclude = $false
    foreach ($pattern in $excludePatterns) {
        if ($file -like $pattern) { $exclude = $true; break }
    }
    
    if (-not $exclude -and $_.Extension -in @(".bat", ".ps1", ".fish", ".nu", ".csh", ".cmd", ".cfg", ".json", ".yaml", ".yml", ".md", ".sh", ".py", ".txt", "")) {
        if ($_.Name -notmatch "\.exe$") {
            try {
                $content = Get-Content $file -Raw -ErrorAction Stop
                if ($content -and ($content -match "C:\\Users\\krish\\AppData\\Local\\ares" -or $content -match "C:\Users\krish\AppData\Local\ares")) {
                    Write-Host "Updating paths in: $file" -ForegroundColor Gray
                    $content = $content -replace "C:\\Users\\krish\\AppData\\Local\\ares", "C:\Users\krish\AppData\Local\ares"
                    $content = $content -replace "C:\Users\krish\AppData\Local\ares", "C:\Users\krish\AppData\Local\ares"
                    $content | Set-Content $file -Force -ErrorAction Stop
                }
            } catch {
                # Skip files that can't be read/written
            }
        }
    }
}

# D. Executable copying
$scriptsDir = Join-Path $aresDir "ares-agent\venv\Scripts"
if (Test-Path $scriptsDir) {
    Write-Host "Cloning executables to ares..." -ForegroundColor Yellow
    if (Test-Path (Join-Path $scriptsDir "ares.exe")) {
        Copy-Item -Path (Join-Path $scriptsDir "ares.exe") -Destination (Join-Path $scriptsDir "ares.exe") -Force
    }
    if (Test-Path (Join-Path $scriptsDir "ares-agent.exe")) {
        Copy-Item -Path (Join-Path $scriptsDir "ares-agent.exe") -Destination (Join-Path $scriptsDir "ares-agent.exe") -Force
    }

    # E. Update ares wrappers to use ares.exe
    $aresBat = Join-Path $scriptsDir "ares.bat"
    $aresBash = Join-Path $scriptsDir "ares"
    if (Test-Path $aresBat) {
        '@echo off' + "`r`n" + '"C:\Users\krish\AppData\Local\ares\ares-agent\venv\Scripts\ares.exe" %*' | Set-Content $aresBat -Force
    }
    if (Test-Path $aresBash) {
        '#!/usr/bin/env bash' + "`n" + 'exec "C:\Users\krish\AppData\Local\ares\ares-agent\venv\Scripts\ares.exe" "$@"' | Set-Content $aresBash -Force
    }
}

Write-Host "Migration completed successfully!" -ForegroundColor Green

