param(
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

$versionSource = Get-Content "src\cargos_downloader\__init__.py" -Raw
$versionMatch = [regex]::Match(
    $versionSource,
    '(?m)^__version__\s*=\s*"(?<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)"\s*$'
)
if (!$versionMatch.Success) {
    throw "No se encontro una version SemVer valida en src\cargos_downloader\__init__.py"
}

$version = $versionMatch.Groups["version"].Value
$numericVersionMatch = [regex]::Match($version, '^(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)')
$major = [int]$numericVersionMatch.Groups["major"].Value
$minor = [int]$numericVersionMatch.Groups["minor"].Value
$patch = [int]$numericVersionMatch.Groups["patch"].Value

if (!(Test-Path "sgd_service.json")) {
    throw "Falta sgd_service.json. Debe existir para construir el paquete distribuible."
}

$versionFile = Join-Path $projectRoot "build\windows-version-info.txt"
New-Item -ItemType Directory -Path (Split-Path $versionFile -Parent) -Force | Out-Null
@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($major, $minor, $patch, 0),
    prodvers=($major, $minor, $patch, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [
          StringStruct(u'CompanyName', u'Gobierno Regional de Huanuco'),
          StringStruct(u'FileDescription', u'SGD Cargos Downloader'),
          StringStruct(u'FileVersion', u'$version'),
          StringStruct(u'InternalName', u'SGD-Cargos-Downloader'),
          StringStruct(u'OriginalFilename', u'SGD-Cargos-Downloader.exe'),
          StringStruct(u'ProductName', u'SGD Cargos Downloader'),
          StringStruct(u'ProductVersion', u'$version')
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@ | Set-Content -LiteralPath $versionFile -Encoding UTF8

if ($SkipDependencyInstall) {
    if (!(Test-Path ".venv\Scripts\pyinstaller.exe")) {
        throw "No existe PyInstaller en .venv. Ejecute el script sin -SkipDependencyInstall."
    }
} else {
    if (!(Test-Path ".venv")) {
        py -3 -m venv .venv
    }

    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

.\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "SGD-Cargos-Downloader" `
    --version-file $versionFile `
    --paths "src" `
    "src\cargos_downloader\main.py"

Copy-Item "sgd_service.json" "dist\sgd_service.json" -Force

$releaseName = "SGD-Cargos-Downloader-$version-win64"
$stagingDir = Join-Path $projectRoot "build\$releaseName"
$releaseDir = Join-Path $projectRoot "dist\releases"
$zipPath = Join-Path $releaseDir "$releaseName.zip"

if (Test-Path $stagingDir) {
    Remove-Item -LiteralPath $stagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Copy-Item "dist\SGD-Cargos-Downloader.exe" $stagingDir
Copy-Item "sgd_service.json" $stagingDir
Copy-Item "CHANGELOG.md" $stagingDir

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath

$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
$checksumPath = Join-Path $releaseDir "$releaseName.sha256.txt"
"$hash  $releaseName.zip" | Set-Content -LiteralPath $checksumPath -Encoding ASCII

Write-Host "Release generado: $zipPath"
Write-Host "Checksum SHA-256: $checksumPath"
