$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m cargos_downloader.main
