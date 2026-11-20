param(
    [string]$NxPath = 'D:\softwares\NX2506\NXBIN\ugraf.exe',
    [int]$Port = 8765
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

# The smoke journal creates or reopens the deterministic test part when this
# flag is inherited by the interactive NX process.
$env:DRAWGEN_CREATE_FIXTURE = 'explicit'

& (Join-Path $PSScriptRoot 'build_branch_c.ps1') -NxPath $NxPath
if ($LASTEXITCODE -ne 0) {
    throw "Branch C build step failed with exit code $LASTEXITCODE"
}

Write-Host ''
Write-Host 'Starting NX and the Branch C browser assistant.'
Write-Host 'After NX opens, use Tools > Journal > Play and select:'
Write-Host (Join-Path $repo 'nx_bridge\BranchCSmokeJournal.cs')
Write-Host 'The browser health card will turn ready after the journal starts.'
Write-Host ''

& (Join-Path $PSScriptRoot 'start_branch_c_ui.ps1') -NxPath $NxPath -Backend bridge -Port $Port
