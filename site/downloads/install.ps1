$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:MEMINGO_REPO_URL) { $env:MEMINGO_REPO_URL } else { "https://github.com/Reaccionador2Jeje/Memingo/archive/refs/heads/main.zip" }
$InstallDir = if ($env:MEMINGO_INSTALL_DIR) { $env:MEMINGO_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA "Memingo" }
$BinDir = Join-Path $InstallDir "bin"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("memingo-" + [guid]::NewGuid())
$ArchivePath = Join-Path $TempDir "memingo.zip"
New-Item -ItemType Directory -Force -Path $TempDir, $InstallDir, $BinDir | Out-Null

$Python = $env:MEMINGO_PYTHON
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source }
if (-not $Python) { $Python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source }
if (-not $Python) {
  throw "Memingo needs Python 3.10 or newer. Install Python 3 from python.org or the Microsoft Store, then run this installer again."
}

$PythonArgs = if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") { @("-3") } else { @() }
& $Python @PythonArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Memingo needs Python 3.10 or newer." }

try {
  Invoke-WebRequest -Uri $RepoUrl -OutFile $ArchivePath -UseBasicParsing
  Expand-Archive -LiteralPath $ArchivePath -DestinationPath $TempDir -Force
  $SourceDir = Get-ChildItem -Path $TempDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName "memingo") } | Select-Object -First 1
  if (-not $SourceDir) { throw "The downloaded archive does not contain the Memingo runtime." }

  $PackageDir = Join-Path $InstallDir "memingo"
  if (Test-Path $PackageDir) { Remove-Item -Recurse -Force $PackageDir }
  Copy-Item -Recurse (Join-Path $SourceDir.FullName "memingo") $PackageDir
  Copy-Item -Force (Join-Path $SourceDir.FullName "scripts/launcher.py") (Join-Path $InstallDir "launcher.py")
  Copy-Item -Force (Join-Path $SourceDir.FullName "scripts/mgoa.py") (Join-Path $InstallDir "mgoa.py")

  $CmdPath = Join-Path $BinDir "memingo.cmd"
  if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") {
    $LauncherArgs = 'py -3 -I "%MEMINGO_HOME%\launcher.py" %*'
  } else {
    $LauncherArgs = '"' + $Python + '" -I "%MEMINGO_HOME%\launcher.py" %*'
  }
  @('@echo off', "set " + '"MEMINGO_HOME=' + $InstallDir + '"', $LauncherArgs) | Set-Content -Encoding ASCII $CmdPath

  $MgoaPath = Join-Path $BinDir "mgoa.cmd"
  if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") {
    $MgoaArgs = 'py -3 -I "%MEMINGO_HOME%\mgoa.py" %*'
  } else {
    $MgoaArgs = '"' + $Python + '" -I "%MEMINGO_HOME%\mgoa.py" %*'
  }
  @('@echo off', "set " + '"MEMINGO_HOME=' + $InstallDir + '"', $MgoaArgs) | Set-Content -Encoding ASCII $MgoaPath

  $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $PathEntries = @($UserPath -split ';' | Where-Object { $_ })
  if ($PathEntries -notcontains $BinDir) {
    [Environment]::SetEnvironmentVariable("Path", (($PathEntries + $BinDir) -join ';'), "User")
  }
  $env:Path = "$BinDir;$env:Path"

  Write-Host "Memingo installed successfully."
  Write-Host "Runtime: $InstallDir"
  Write-Host "Commands: $CmdPath and $MgoaPath"
  Write-Host "Open a new terminal and run: memingo --version"
}
finally {
  Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}
