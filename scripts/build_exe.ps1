# Compila ConciliacionCreditoFiscal.exe con un venv limpio.
# El trabajo y la salida van a %LOCALAPPDATA% para evitar bloqueos de OneDrive.
$ErrorActionPreference = "Stop"
$EngineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $EngineRoot

$AppName = "ConciliacionCreditoFiscal"
$LegacyAppNames = @("ConciliacionAMARAL")

$Venv = Join-Path $EngineRoot ".venv-build"
if (-not (Test-Path $Venv)) {
    Write-Host "Creando venv en $Venv"
    py -3 -m venv $Venv
}

$Py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Py)) {
    throw "No se encontro Python en el venv: $Py"
}

& $Py -m pip install --upgrade pip -q
& $Py -m pip install -r requirements.txt -r requirements-build.txt -q

$WorkPath = Join-Path $env:LOCALAPPDATA "$AppName-pyi-work"
$DistPath = Join-Path $env:LOCALAPPDATA "$AppName-dist"
$SpecFile = Join-Path $PSScriptRoot "conciliation.spec"
$OutFolder = Join-Path $DistPath $AppName
$Exe = Join-Path $OutFolder "$AppName.exe"

function Remove-DirRetry {
    param([string]$Path, [int]$Attempts = 5)
    if (-not (Test-Path $Path)) { return }
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            if ($i -eq $Attempts) { throw }
            Start-Sleep -Seconds 2
        }
    }
}

Write-Host "Cerrando $AppName (y nombres antiguos) si estan en ejecucion..."
foreach ($proc in @($AppName) + $LegacyAppNames) {
    Get-Process -Name $proc -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

Write-Host "Limpiando carpetas de compilacion..."
Remove-DirRetry -Path $WorkPath
Remove-DirRetry -Path $DistPath

Write-Host "Compilando (fuera de OneDrive)..."
& $Py -m PyInstaller $SpecFile `
    --noconfirm `
    --workpath $WorkPath `
    --distpath $DistPath

if (-not (Test-Path $Exe)) {
    throw "Compilacion fallida: no se encontro $Exe"
}

# Copia opcional a dist del proyecto (conveniencia)
$ProjectDist = Join-Path $EngineRoot "dist\$AppName"
$ProjectExe = Join-Path $ProjectDist "$AppName.exe"
Write-Host ""
Write-Host "Compilacion OK:"
Write-Host "  $Exe"
Write-Host ""
Write-Host "Copiando a dist del proyecto..."
try {
    if (Test-Path $ProjectDist) { Remove-DirRetry -Path $ProjectDist -Attempts 3 }
    New-Item -ItemType Directory -Path (Split-Path $ProjectDist) -Force | Out-Null
    Copy-Item -Path $OutFolder -Destination $ProjectDist -Recurse -Force
    Write-Host "  Also at: $ProjectExe"
} catch {
    Write-Warning "No se pudo copiar a dist en OneDrive (carpeta bloqueada). Use la compilacion en LocalAppData."
    Write-Warning $_.Exception.Message
}

Write-Host ""
Write-Host "Distribuya esta carpeta completa en otras PCs:"
Write-Host "  $OutFolder"
