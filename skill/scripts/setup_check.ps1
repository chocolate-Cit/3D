# parking-site-3d: check a computer is ready (run once after copying the skill to a new machine).
#   powershell -ExecutionPolicy Bypass -File setup_check.ps1 [-Fix]
#   -Fix installs Pillow with pip and saves the Blender path in the user env var BLENDER_EXE.
param([switch]$Fix)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$ok = $true
function Say($good, $msg) { if ($good) { Write-Host "[OK]   $msg" -ForegroundColor Green } else { Write-Host "[MISS] $msg" -ForegroundColor Yellow; $script:ok = $false } }

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
Say ([bool]$py) "Python launcher (py) - install Python 3 from python.org (tick 'Add to PATH')"
if ($py) {
  & $py.Source -c "import PIL" 2>$null
  $pil = ($LASTEXITCODE -eq 0)
  if (-not $pil -and $Fix) { & $py.Source -m pip install --user pillow; & $py.Source -c "import PIL" 2>$null; $pil = ($LASTEXITCODE -eq 0) }
  Say $pil "Pillow (py -m pip install pillow)"
}

$bl = & "$here\find_blender.ps1"
Say ([bool]$bl) "Blender 4.2+ (blender.org or Steam). Found: $bl"
if ($bl) {
  $ver = (& $bl -b --factory-startup --version 2>$null | Select-Object -First 1)
  Write-Host "       $ver"
  if ($Fix -and -not [Environment]::GetEnvironmentVariable('BLENDER_EXE', 'User')) {
    [Environment]::SetEnvironmentVariable('BLENDER_EXE', $bl, 'User'); Write-Host "       saved BLENDER_EXE for this user"
  }
}

Say (Test-Path "$env:WINDIR\Fonts\tahoma.ttf") "Tahoma font (Thai text on 3D signs / plates)"
$assets = @('hdri', 'textures\asphalt_02', 'textures\leafy_grass', 'textures\concrete_floor_02', 'textures\interlocking_concrete_pavers')
$cache = Join-Path $env:LOCALAPPDATA 'parking-site-3d\assets'
$has = { param($b) -not ($assets | Where-Object { -not (Test-Path "$b\$_") }) }
$aok = (& $has "$root\assets") -or (& $has $cache)
if (-not $aok -and $Fix -and $py) { & $py.Source -I "$here\fetch_assets.py"; $aok = (& $has "$root\assets") -or (& $has $cache) }
Say $aok "Poly Haven textures + sky (skill assets\ or $cache) - fix: py -I `"$here\fetch_assets.py`" (internet, ~14 MB)"

if ($ok) { Write-Host "`nREADY - try: powershell -ExecutionPolicy Bypass -File `"$here\run.ps1`" `"$root\examples\sample_site.json`" `"$env:TEMP\parking_test`" -Samples 16" -ForegroundColor Green }
else { Write-Host "`nFix the [MISS] lines above (or rerun with -Fix)." -ForegroundColor Yellow }
