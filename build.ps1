$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

# --onedir (the default, so no --onefile flag) instead of a single
# self-extracting exe: onefile's runtime self-extraction into a temp
# directory is exactly the behavior pattern antivirus heuristics associate
# with malware droppers, and unpacking everything at build time instead
# measurably reduces false-positive detections for an unsigned exe like
# this one.
& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "RekordboxNowPlaying" `
    --icon "$PSScriptRoot\app_icon.ico" `
    "$PSScriptRoot\main.py"

$distDir = Join-Path $PSScriptRoot "dist\RekordboxNowPlaying"
$zipPath = Join-Path $PSScriptRoot "dist\RekordboxNowPlaying.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Compress-Archive -Path "$distDir\*" -DestinationPath $zipPath

Write-Host ""
Write-Host "Built: $zipPath"
