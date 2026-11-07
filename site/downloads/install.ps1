$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:MEMINGO_REPO_URL) { $env:MEMINGO_REPO_URL } else { "https://github.com/Reaccionador2Jeje/Memingo/archive/refs/heads/main.zip" }
$InstallDir = if ($env:MEMINGO_INSTALL_DIR) { $env:MEMINGO_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA "Memingo" }
$BinDir = Join-Path $InstallDir "bin"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("memingo-" + [guid]::NewGuid())
$ArchivePath = Join-Path $TempDir "memingo.zip"
New-Item -ItemType Directory -Force -Path $TempDir, $InstallDir, $BinDir | Out-Null

$Python = $env:MEMINGO_PYTHON
if (-not $Python) { $Python = (Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1).Source }
if (-not $Python) { $Python = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source }
if (-not $Python) { throw "Memingo needs Python 3.10 or newer." }

$PythonArgs = if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") { @("-3") } else { @() }
& $Python @PythonArgs -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if ($LASTEXITCODE -ne 0) { throw "Memingo needs Python 3.10 or newer." }

try {
  Invoke-WebRequest -Uri $RepoUrl -OutFile $ArchivePath
  Expand-Archive -Path $ArchivePath -DestinationPath $TempDir -Force
  $SourceDir = Get-ChildItem -Path $TempDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName "memingo") } | Select-Object -First 1
  if (-not $SourceDir) { throw "Could not find the Memingo runtime in the download." }

  $PackageDir = Join-Path $InstallDir "memingo"
  if (Test-Path $PackageDir) { Remove-Item -Recurse -Force $PackageDir }
  Copy-Item -Recurse (Join-Path $SourceDir.FullName "memingo") $PackageDir
  Copy-Item (Join-Path $SourceDir.FullName "scripts/launcher.py") (Join-Path $InstallDir "launcher.py")

  $CmdPath = Join-Path $BinDir "memingo.cmd"
  $LauncherArgs = if ([System.IO.Path]::GetFileName($Python) -eq "py.exe") {
    'py -3 -I "%MEMINGO_HOME%\launcher.py" %*'
  } else {
    '"' + $Python + '" -I "%MEMINGO_HOME%\launcher.py" %*'
  }
  @('@echo off', "set `"MEMINGO_HOME=$InstallDir`"", $LauncherArgs) | Set-Content -Encoding ASCII $CmdPath

  $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $PathEntries = @($UserPath -split ';' | Where-Object { $_ })
  if ($PathEntries -notcontains $BinDir) {
    [Environment]::SetEnvironmentVariable("Path", (($PathEntries + $BinDir) -join ';'), "User")
  }
  $env:Path = "$BinDir;$env:Path"
  Write-Host "Memingo installed at $InstallDir"
  Write-Host "Open a new terminal and run: memingo"
}
finally {
  Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}
