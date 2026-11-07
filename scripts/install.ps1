$ErrorActionPreference = "Stop"

$SourceDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallDir = if ($env:MEMINGO_INSTALL_DIR) {
    $env:MEMINGO_INSTALL_DIR
} else {
    Join-Path $env:LOCALAPPDATA "Memingo"
}
$BinDir = Join-Path $InstallDir "bin"

$Python = $env:MEMINGO_PYTHON
if (-not $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
}
if (-not $Python) {
    $Python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
}

if (-not $Python) {
    throw "Memingo needs Python 3.10 or newer. Install Python from https://www.python.org/downloads/windows/."
}

$PythonArgs = if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") { @("-3") } else { @() }
& $Python @PythonArgs -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if ($LASTEXITCODE -ne 0) {
    throw "Memingo needs Python 3.10 or newer."
}

New-Item -ItemType Directory -Force -Path $InstallDir, $BinDir | Out-Null
$PackageDir = Join-Path $InstallDir "memingo"
if (Test-Path $PackageDir) {
    Remove-Item -Recurse -Force $PackageDir
}
Copy-Item -Recurse (Join-Path $SourceDir "memingo") $PackageDir
Copy-Item (Join-Path $PSScriptRoot "launcher.py") (Join-Path $InstallDir "launcher.py")

$CmdPath = Join-Path $BinDir "memingo.cmd"
$LauncherArgs = if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") {
    'py -3 -I "%MEMINGO_HOME%\launcher.py" %*'
} else {
    '"' + $Python + '" -I "%MEMINGO_HOME%\launcher.py" %*'
}
@(
    '@echo off',
    "set " + '"MEMINGO_HOME=' + $InstallDir + '"',
    $LauncherArgs
) | Set-Content -Encoding ASCII $CmdPath

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathEntries = @($UserPath -split ';' | Where-Object { $_ })
if ($PathEntries -notcontains $BinDir) {
    $NewPath = (($PathEntries + $BinDir) -join ';')
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
}
$env:Path = "$BinDir;$env:Path"

Write-Host "Memingo installed at $InstallDir"
Write-Host "Command installed at $CmdPath"
Write-Host "Open a new terminal and run: memingo"
