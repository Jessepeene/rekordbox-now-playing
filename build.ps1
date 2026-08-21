$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "RekordboxNowPlaying" `
    --icon "$PSScriptRoot\app_icon.ico" `
    "$PSScriptRoot\main.py"

Write-Host ""
Write-Host "Built: $PSScriptRoot\dist\RekordboxNowPlaying.exe"
