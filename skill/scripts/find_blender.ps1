# parking-site-3d: print the path of the newest blender.exe on this computer (nothing if none).
# Order: $env:BLENDER_EXE, user env var, PATH, Program Files, Steam libraries on every drive.
$c = @()
foreach ($v in @($env:BLENDER_EXE, [Environment]::GetEnvironmentVariable('BLENDER_EXE', 'User'))) { if ($v -and (Test-Path $v)) { $v; return } }
$cmd = Get-Command blender.exe -ErrorAction SilentlyContinue
if ($cmd) { $cmd.Source; return }
$roots = @("$env:ProgramFiles\Blender Foundation", "${env:ProgramFiles(x86)}\Steam\steamapps\common\Blender", "$env:LOCALAPPDATA\Programs\Blender Foundation")
foreach ($d in (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue)) {
  $roots += "$($d.Root)Steam\steamapps\common\Blender", "$($d.Root)SteamLibrary\steamapps\common\Blender", "$($d.Root)Program Files\Steam\steamapps\common\Blender"
}
foreach ($r in $roots) {
  if ($r -and (Test-Path $r)) { $c += Get-ChildItem $r -Recurse -Filter blender.exe -ErrorAction SilentlyContinue }
}
$c | Sort-Object { $_.VersionInfo.FileVersion } -Descending | Select-Object -First 1 -ExpandProperty FullName
