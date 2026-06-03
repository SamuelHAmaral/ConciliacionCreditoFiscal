# Empaqueta la carpeta PyInstaller en ZIP para GitHub Releases o distribucion manual.
# Ejecutar despues de scripts\build_exe.ps1
param(
    [string]$Version = "snapshot",
    [string]$AppName = "ConciliacionCreditoFiscal"
)

$ErrorActionPreference = "Stop"
$EngineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $EngineRoot

$Source = Join-Path $env:LOCALAPPDATA "$AppName-dist\$AppName"
if (-not (Test-Path (Join-Path $Source "$AppName.exe"))) {
    $Alt = Join-Path $EngineRoot "dist\$AppName"
    if (Test-Path (Join-Path $Alt "$AppName.exe")) {
        $Source = $Alt
    } else {
        throw "No se encontro la app compilada. Ejecute: powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1"
    }
}

$DistDir = Join-Path $EngineRoot "dist"
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

$SafeVersion = ($Version -replace '^refs/tags/v', '' -replace '^v', '' -replace '[^\w.\-]', '_')
if (-not $SafeVersion) { $SafeVersion = "snapshot" }

$ZipName = "$AppName-Windows-x64-$SafeVersion.zip"
$ZipPath = Join-Path $DistDir $ZipName
$Stage = Join-Path $env:TEMP "$AppName-release-stage-$SafeVersion"

if (Test-Path $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
New-Item -ItemType Directory -Path $Stage | Out-Null

Write-Host "Preparando desde $Source"
Copy-Item -Path $Source -Destination (Join-Path $Stage $AppName) -Recurse -Force

$Leeme = Join-Path $EngineRoot "docs\LEEME.txt"
if (Test-Path $Leeme) {
    Copy-Item -Path $Leeme -Destination (Join-Path $Stage "LEEME.txt") -Force
}

if (Test-Path $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -CompressionLevel Optimal

Remove-Item -LiteralPath $Stage -Recurse -Force

$SizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "ZIP de release listo:"
Write-Host "  $ZipPath"
Write-Host "  Tamano: ${SizeMb} MB"
Write-Host ""
Write-Host "Suba este archivo a GitHub Releases (Assets)."
