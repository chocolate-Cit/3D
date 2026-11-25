# parking-site-3d: full pipeline.
#   powershell -File run.ps1 <site.json> [out_dir] [-NoRender] [-Samples 64] [-Res 1600x900]
param(
  [Parameter(Mandatory=$true)][string]$Site,
  [string]$Out = "",
  [switch]$NoRender,
  [int]$Samples = 64,
  [string]$Res = "1600x900"
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Out) { $Out = Join-Path (Split-Path -Parent (Resolve-Path $Site)) 'out' }
$blender = $env:BLENDER_EXE
if (-not $blender) { $blender = [Environment]::GetEnvironmentVariable('BLENDER_EXE', 'User') }
if (-not $blender) { $blender = & "$here\find_blender.ps1" }
if (-not $blender) { throw 'Blender not found: install Blender 4.2+ or set $env:BLENDER_EXE (run setup_check.ps1)' }
$cache = Join-Path $env:LOCALAPPDATA 'parking-site-3d\assets'
if (-not (Test-Path "$here\..\assets\hdri\*.hdr") -and -not (Test-Path "$cache\hdri\*.hdr")) {   # first run: fetch CC0 textures + sky
  py -I "$here\fetch_assets.py"; if ($LASTEXITCODE -ne 0) { Write-Warning 'asset download failed: using procedural materials' }
}
py "$here\site_layout.py" $Site $Out
if ($LASTEXITCODE -ne 0) { throw 'layout failed' }
$args_ = @('-b', '--factory-startup', '--python', "$here\build_blender.py", '--', "$Out\layout.json", $Out, '--samples', $Samples, '--res', $Res)
if ($NoRender) { $args_ += '--no-render' }
$ErrorActionPreference = 'Continue'   # Blender writes warnings to stderr
& $blender @args_ 2>&1 | Where-Object { $_ -match 'EXPORT_OK|RENDERED|BUILD_OK|Error|Traceback|File "' } | ForEach-Object { "$_" }
if (-not (Test-Path "$Out\site.glb")) { throw 'Blender build failed (no site.glb)' }
if (Select-String -Path "$Out\layout.json" -Pattern '"lpr_camera"' -Quiet) {      # LPR sight-line / clearance check
  & $blender -b "$Out\site.blend" --python "$here\check_lpr.py" -- "$Out\layout.json" "$Out\lpr_check.json" 2>&1 | Where-Object { $_ -match '^LPR_CHECK|"status": "CHECK"' } | ForEach-Object { "$_" }
}
& $blender -b "$Out\site.blend" --python "$here\check_pads.py" -- "$Out\layout.json" 2>&1 | Where-Object { $_ -match '^PAD_CHECK|^OVERHANG' } | ForEach-Object { "$_" }
py "$here\make_viewer.py" $Out
"DONE -> $Out"
