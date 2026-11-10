# Build the PCSF Studio executable and installer on Windows.
#
#   powershell -ExecutionPolicy Bypass -File installers\build.ps1
#   ... -NoPackage     freeze and self-test only
#   ... -Setup         first install the build requirements
#   ... -Python C:\path\to\envs\pcsf-venv\python.exe
#
# Output: dist\pcsf-studio\pcsf-studio.exe and, when Inno Setup 6 is
# installed, dist\pcsf-studio-<version>-setup.exe.
param(
    [string]$Python = "",
    [switch]$NoPackage,
    [switch]$Setup
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { throw "no Python found; pass -Python" }
    $Python = $cmd.Source
}
Push-Location $Root
try {
    if ($Setup) {
        & $Python -m pip install -e ".[studio,emc,mare2dem]" pyinstaller
        if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    }
    & $Python -c "import PySide6, PyInstaller"
    if ($LASTEXITCODE -ne 0) {
        throw "PySide6 or PyInstaller missing in $Python; use -Setup"
    }
    Write-Host "building with $Python"
    $extra = @()
    if ($NoPackage) { $extra += "--no-package" }
    & $Python installers\build.py @extra
    if ($LASTEXITCODE -ne 0) { throw "build failed" }
}
finally {
    Pop-Location
}
