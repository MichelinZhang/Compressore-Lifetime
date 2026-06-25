# Compressor Lifetime Rev 3.2.6 - Nuitka one-click build (Windows)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1 -Clean
#
# Prerequisites:
#   1. Python 3.10+ venv at .venv with: pip install -r requirements-ni.txt
#   2. MSVC Build Tools OR auto-download MinGW64 (first build may take 15-30 min)
#   3. Target PC must install NI-DAQmx Runtime (not bundled in exe)
#
# Output:
#   dist\CompressorLifetime\CompressorLifetime.dist\CompressorLifetime.exe

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Entry = "compressor_lifetime_3_2_6.py"
$OutDir = Join-Path $Root "dist\CompressorLifetime"
$ProductVersion = "3.2.6"

if (-not (Test-Path $VenvPython)) {
    Write-Error @"
Virtual env not found: $VenvPython

Setup:
  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements-ni.txt
"@
}

if (-not (Test-Path (Join-Path $Root $Entry))) {
    Write-Error "Entry script not found: $Entry"
}

& $VenvPython -m nuitka --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Nuitka not installed. Run: .\.venv\Scripts\pip install -r requirements-ni.txt"
}

if ($Clean -and (Test-Path $OutDir)) {
    Write-Host "Cleaning $OutDir ..."
    Remove-Item -Recurse -Force $OutDir
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "=========================================="
Write-Host " Compressor Lifetime Nuitka Build $ProductVersion"
Write-Host "=========================================="
Write-Host "  Entry   : $Entry"
Write-Host "  Output  : $OutDir"
Write-Host ""

$CompilerArgs = @()
if ($env:VCINSTALLDIR -or (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "  Compiler: MSVC (Visual Studio)"
} else {
    Write-Host "  Compiler: MinGW64 (--mingw64, auto-download on first run)"
    $CompilerArgs += "--mingw64"
}

$BuildStart = Get-Date

& $VenvPython -m nuitka `
    --standalone `
    --assume-yes-for-downloads `
    --enable-plugin=pyqt6 `
    --include-package=nidaqmx `
    --nofollow-import-to=scipy,matplotlib,PIL `
    --output-dir="$OutDir" `
    --output-filename=CompressorLifetime `
    --windows-console-mode=disable `
    --company-name="Fresenius Medical Care" `
    --product-name="Compressor Lifetime Test" `
    --file-version="$ProductVersion.0" `
    --product-version="$ProductVersion" `
    --jobs=1 `
    --show-progress `
    @CompilerArgs `
    $Entry

if ($LASTEXITCODE -ne 0) {
    Write-Error "Nuitka build failed (exit $LASTEXITCODE). See nuitka-crash-report.xml if present."
}

$Elapsed = (Get-Date) - $BuildStart
$ExeCandidates = Get-ChildItem -Path $OutDir -Recurse -Filter "CompressorLifetime.exe" -ErrorAction SilentlyContinue

if ($ExeCandidates) {
    $ExePath = $ExeCandidates[0].FullName
    $DistDir = $ExeCandidates[0].DirectoryName
    Write-Host ""
    Write-Host "Build succeeded in $($Elapsed.ToString('mm\:ss'))"
    Write-Host "  EXE : $ExePath"
    Write-Host "  Dist: $DistDir  (copy entire folder to target PC)"
    Write-Host ""
    Write-Host "Deploy notes:"
    Write-Host "  - Install NI-DAQmx Runtime on target machine"
    Write-Host "  - Run CompressorLifetime.exe from the .dist folder"
} else {
    Write-Warning "Build finished but CompressorLifetime.exe not found under $OutDir"
    Get-ChildItem -Path $OutDir -Recurse | Select-Object -First 20 FullName
    exit 1
}
