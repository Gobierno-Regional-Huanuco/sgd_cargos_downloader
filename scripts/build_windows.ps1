$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

if (!(Test-Path ".venv")) {
    py -3 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "SGD-Cargos-Downloader" `
    --paths "src" `
    "src\cargos_downloader\main.py"

Copy-Item "sgd_service.json" "dist\sgd_service.json" -Force
