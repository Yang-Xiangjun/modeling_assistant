param(
    [string]$NxPath = 'D:\softwares\NX2506\NXBIN\ugraf.exe'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$nxRoot = Split-Path -Parent (Split-Path -Parent $NxPath)
$project = Join-Path $repo 'nx_bridge\NxBridge.csproj'

if (-not (Test-Path -LiteralPath $NxPath)) {
    throw "NX executable was not found at $NxPath"
}
if (-not (Test-Path -LiteralPath $project)) {
    throw "Branch C project was not found at $project"
}

$env:NX_ROOT = $nxRoot
Write-Host "Building Branch C bridge against $env:NX_ROOT"
& dotnet build $project --no-restore --nologo -v:minimal
if ($LASTEXITCODE -ne 0) {
    throw "Branch C bridge build failed with exit code $LASTEXITCODE"
}

$assembly = Join-Path $repo 'nx_bridge\bin\Debug\net8.0-windows\Drawgen.NxBridgeBranchC.dll'
if (-not (Test-Path -LiteralPath $assembly)) {
    throw "Branch C bridge assembly was not produced at $assembly"
}
Write-Host "Bridge ready: $assembly"

$journalCheck = Join-Path $repo 'tools\check_branch_c_journal.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $journalCheck `
    -Journal (Join-Path $repo 'nx_bridge\BranchCSmokeJournal.cs') `
    -Output (Join-Path $repo 'nx_bridge\obj\BranchCSmokeJournal.check.dll') `
    -NxRoot $nxRoot
if ($LASTEXITCODE -ne 0) {
    throw "Branch C journal type check failed with exit code $LASTEXITCODE"
}
