# ParkingSite3D kit: prove this computer builds the SAME 3D models as the original computer.
#   powershell -ExecutionPolicy Bypass -File verify.ps1             -> MATCH / DIFFERENT per case
#   powershell -ExecutionPolicy Bypass -File verify.ps1 -MakeReference   (original computer only: save new references)
param([switch]$MakeReference)
$K = Split-Path -Parent $MyInvocation.MyCommand.Path
$S = "$env:USERPROFILE\.claude\skills\parking-site-3d\scripts"
if (-not (Test-Path "$S\build_blender.py")) { Write-Host "Skill not installed - run install.ps1 first" -ForegroundColor Red; exit 1 }
$bl = & "$S\find_blender.ps1"
if (-not $bl) { Write-Host "Blender not found - run install.ps1 first" -ForegroundColor Red; exit 1 }
Write-Host "Blender: $bl"
$cases = [ordered]@{
  'sample'            = "$env:USERPROFILE\.claude\skills\parking-site-3d\examples\sample_site.json"
  'campus_5_gates'    = "$K\projects\campus_5_gates\site_compact.json"
  'hardware_library'  = "$K\libraries\hardware_library\site.json"
  'building_library'  = "$K\libraries\building_library\site.json"
}
$fail = 0
foreach ($name in $cases.Keys) {
  $out = Join-Path $env:TEMP "ps3d_verify\$name"
  if (Test-Path $out) { Remove-Item $out -Recurse -Force }
  py "$S\site_layout.py" $cases[$name] $out | Out-Null
  $ErrorActionPreference = 'Continue'
  & $bl -b --factory-startup --python "$S\build_blender.py" -- "$out\layout.json" $out --no-render 2>$null | Out-Null
  $ErrorActionPreference = 'Stop'
  $ref = "$K\reference\$name.json"
  if ($MakeReference) {
    py "$S\fingerprint.py" $out | Out-File -Encoding ascii $ref; Write-Host "saved $ref"
  } else {
    $r = py "$S\fingerprint.py" $out $ref
    if ($LASTEXITCODE -eq 0) { Write-Host ("[MATCH]     {0}" -f $name) -ForegroundColor Green }
    else { $fail++; Write-Host ("[DIFFERENT] {0}  {1}" -f $name, $r) -ForegroundColor Red }
  }
}
if (-not $MakeReference) {
  if ($fail -eq 0) { Write-Host "`nALL MATCH - this computer builds exactly the same models." -ForegroundColor Green }
  else { Write-Host "`n$fail case(s) differ: check the Blender version (must be the kit's 5.3.0) and that skill\ was installed from this kit." -ForegroundColor Red }
}
