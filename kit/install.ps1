# ParkingSite3D kit: set up a computer so it builds exactly what the original computer built.
#   Right-click > Run with PowerShell, or: powershell -ExecutionPolicy Bypass -File install.ps1
# 1) Blender 5.3.0 from the kit (unzipped to %LOCALAPPDATA%\ParkingSite3D, does not touch any other Blender)
# 2) the skill from the kit -> %USERPROFILE%\.claude\skills\parking-site-3d (an older copy is kept as a backup)
# 3) Pillow 13.0.0   4) verify.ps1
#   Blender folder: -InstallDir D:\ParkingSite3D   (use this if Blender fails to start from %LOCALAPPDATA%,
#   e.g. "side-by-side configuration is incorrect")
param([string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'ParkingSite3D'))
$ErrorActionPreference = 'Stop'
$K = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "Python not found. Install Python 3.11 from python.org (tick 'Add python.exe to PATH'), then run this again." -ForegroundColor Red; exit 1 }

$home3d = $InstallDir
$bl = Join-Path $home3d 'Blender\blender.exe'
if (-not (Test-Path $bl)) {
  Write-Host "Unpacking Blender 5.3.0 (about 1 GB, takes a minute)..."
  New-Item -ItemType Directory -Force $home3d | Out-Null
  tar -x -f "$K\blender\blender-5.3.0-windows.zip" -C $home3d
}
# Make sure this Blender actually starts before going on
try { $blenderVersion = & $bl --version 2>$null | Select-Object -First 1 } catch { $blenderVersion = $null }
if ($blenderVersion -notmatch 'Blender 5\.3\.0') {
  Write-Host "Blender at $bl does not start on this computer." -ForegroundColor Red
  Write-Host "Run again with another folder, e.g.: powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir D:\ParkingSite3D" -ForegroundColor Red
  exit 1
}
[Environment]::SetEnvironmentVariable('BLENDER_EXE', $bl, 'User'); $env:BLENDER_EXE = $bl
Write-Host "Blender: $bl"

$dst = "$env:USERPROFILE\.claude\skills\parking-site-3d"
if (Test-Path $dst) {
  $bak = "$env:USERPROFILE\.claude\skills-backup\parking-site-3d-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
  New-Item -ItemType Directory -Force (Split-Path $bak) | Out-Null
  Move-Item $dst $bak; Write-Host "Old skill kept at $bak"
}
New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
Copy-Item "$K\skill\parking-site-3d" $dst -Recurse
Write-Host "Skill installed: $dst"

& $py.Source -m pip install --user --quiet pillow==13.0.0
Write-Host "Pillow 13.0.0 ready"

& "$K\verify.ps1"
