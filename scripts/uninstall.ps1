$ErrorActionPreference = "Stop"

$InstallDir = if ($env:MEMINGO_INSTALL_DIR) {
    $env:MEMINGO_INSTALL_DIR
} else {
    Join-Path $env:LOCALAPPDATA "Memingo"
}
$BinDir = Join-Path $InstallDir "bin"

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath) {
    $Entries = @($UserPath -split ';' | Where-Object { $_ -and $_ -ne $BinDir })
    [Environment]::SetEnvironmentVariable("Path", ($Entries -join ';'), "User")
}

Write-Host "Memingo removed from $InstallDir"
