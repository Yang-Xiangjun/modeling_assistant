param(
    [string]$Journal = 'D:\codes\modeling_assistant\nx_bridge\BranchCSmokeJournal.cs',
    [string]$Output = 'D:\codes\modeling_assistant\nx_bridge\obj\BranchCSmokeJournal.check.dll',
    [string]$NxRoot = 'D:\softwares\NX2506'
)

$ErrorActionPreference = 'Stop'
$journalPath = (Resolve-Path -LiteralPath $Journal).Path
$outputPath = [IO.Path]::GetFullPath($Output)
$dotnetRoot = Join-Path ${env:ProgramFiles} 'dotnet'
$sdk = Get-ChildItem (Join-Path $dotnetRoot 'sdk') -Directory |
    Where-Object { $_.Name -match '^8\.' } |
    Sort-Object { [version]$_.Name } -Descending |
    Select-Object -First 1
$referencePack = Get-ChildItem (Join-Path $dotnetRoot 'packs\Microsoft.NETCore.App.Ref') -Directory |
    Where-Object { $_.Name -match '^8\.' } |
    Sort-Object { [version]$_.Name } -Descending |
    Select-Object -First 1

if ($null -eq $sdk -or $null -eq $referencePack) {
    throw 'A .NET 8 SDK and reference pack are required to check the NX journal.'
}

$compiler = Join-Path $sdk.FullName 'Roslyn\bincore\csc.dll'
$references = @(
    Get-ChildItem (Join-Path $referencePack.FullName 'ref\net8.0') -Filter '*.dll' |
        ForEach-Object { '/reference:' + $_.FullName }
)
foreach ($assembly in @('NXOpen.dll', 'NXOpen.UF.dll', 'NXOpen.Utilities.dll')) {
    $references += '/reference:' + (Join-Path $NxRoot ('NXBIN\managed_core\' + $assembly))
}

New-Item -ItemType Directory -Path (Split-Path -Parent $outputPath) -Force | Out-Null
Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
& (Join-Path $dotnetRoot 'dotnet.exe') $compiler /nologo /target:library /nostdlib "/out:$outputPath" @references $journalPath
if ($LASTEXITCODE -ne 0) {
    throw "NX journal type check failed with exit code $LASTEXITCODE"
}
Write-Host "Journal type check passed: $journalPath"
