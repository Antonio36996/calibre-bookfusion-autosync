# Installs or updates the plugin in calibre. Restart calibre afterwards to load it.
$ErrorActionPreference = 'Stop'
& 'C:\Program Files\Calibre2\calibre-customize.exe' -b (Join-Path $PSScriptRoot 'plugin')
