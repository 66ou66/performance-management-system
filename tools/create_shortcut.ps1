# Create the desktop shortcut that launches the whole project with one click.
# All text is ASCII; the Chinese shortcut name is built from code points so that
# the script parses correctly regardless of the console code page / BOM.

$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Split-Path -Parent $toolsDir
$desktop = [Environment]::GetFolderPath('Desktop')

$name = [string]::Join('', [char[]]@(
    0x4E13, 0x4E1A, 0x5E08, 0x751F,
    0x4E1A, 0x7EE9, 0x7BA1, 0x7406,
    0x7CFB, 0x7EDF
))

$target = Join-Path $project 'start_app.bat'
if (-not (Test-Path $target)) {
    throw "Launcher not found: $target"
}

$link = Join-Path $desktop ($name + '.lnk')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $project
$shortcut.WindowStyle = 7
$shortcut.Description = $name + ' - one click launcher'
$icon = Join-Path $project 'assets\app.ico'
if (Test-Path $icon) {
    $shortcut.IconLocation = $icon
}
$shortcut.Save()

$check = $shell.CreateShortcut($link)
Write-Output ('SHORTCUT_CREATED ' + $link)
Write-Output ('TARGET ' + $check.TargetPath)
Write-Output ('ICON ' + $check.IconLocation)
Write-Output ('EXISTS ' + (Test-Path $link))