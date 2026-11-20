param(
    [string]$NxPath = 'D:\softwares\NX2506\NXBIN\ugraf.exe',
    [ValidateSet('bridge', 'mock')][string]$Backend = 'bridge',
    [int]$Port = 8765,
    [switch]$NoFixture
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $repo '.uv-cache'
$env:DRAWGEN_PI_AGENT_DIR = Join-Path $repo '.pi-agent'
$endpoint = Join-Path $env:LOCALAPPDATA 'drawgen\bridge.json'
$env:DRAWGEN_UI_BACKEND = $Backend
$env:DRAWGEN_UI_PORT = [string]$Port
$env:DRAWGEN_BRIDGE_ENDPOINT = $endpoint
$env:DRAWGEN_PI_COMMAND = 'pi.cmd'
$env:DRAWGEN_PI_ARGS = '--print --mode json'
$env:DRAWGEN_PI_SKILL = Join-Path $repo '.pi-agent\skills\nxopen-cad\SKILL.md'
$env:DRAWGEN_UI_AUTO_CONFIRM = '1'
if ($NoFixture) {
    Remove-Item Env:DRAWGEN_CREATE_FIXTURE -ErrorAction SilentlyContinue
} else {
    $env:DRAWGEN_CREATE_FIXTURE = 'explicit'
}

if (-not (Test-Path -LiteralPath $NxPath)) {
    throw "NX executable was not found at $NxPath"
}

$env:UGII_BASE_DIR = Split-Path -Parent (Split-Path -Parent $NxPath)
$env:UGII_ROOT_DIR = Join-Path $env:UGII_BASE_DIR 'UGII'
$nx = Start-Process -FilePath $NxPath -ArgumentList @('-nx') -WorkingDirectory 'C:\ProgramData' -PassThru
$server = Start-Process -FilePath 'uv' -ArgumentList @('run', 'python', (Join-Path $repo 'tools\branch_c_ui_server.py')) -WorkingDirectory $repo -PassThru

Start-Sleep -Seconds 2
$url = "http://127.0.0.1:$Port/"
$browser = Start-Process -FilePath 'msedge.exe' -ArgumentList @('--new-window', $url) -PassThru

Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class BranchCWindow {
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int width, int height, bool repaint);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
}
'@

Add-Type -AssemblyName System.Windows.Forms
$area = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$leftWidth = [Math]::Floor($area.Width * 0.62)
$rightWidth = $area.Width - $leftWidth

function Wait-Window([System.Diagnostics.Process]$Process) {
    for ($i = 0; $i -lt 40; $i++) {
        $Process.Refresh()
        if ($Process.MainWindowHandle -ne [IntPtr]::Zero) { return $Process.MainWindowHandle }
        Start-Sleep -Milliseconds 250
    }
    return [IntPtr]::Zero
}

$nxHandle = Wait-Window $nx
$browserHandle = Wait-Window $browser
if ($null -eq $nxHandle) { $nxHandle = [IntPtr]::Zero }
if ($null -eq $browserHandle) { $browserHandle = [IntPtr]::Zero }
if ($nxHandle -ne [IntPtr]::Zero) {
    [BranchCWindow]::ShowWindow($nxHandle, 9) | Out-Null
    [BranchCWindow]::MoveWindow($nxHandle, $area.Left, $area.Top, $leftWidth, $area.Height, $true) | Out-Null
}
if ($browserHandle -ne [IntPtr]::Zero) {
    [BranchCWindow]::ShowWindow($browserHandle, 9) | Out-Null
    [BranchCWindow]::MoveWindow($browserHandle, $area.Left + $leftWidth, $area.Top, $rightWidth, $area.Height, $true) | Out-Null
}

Write-Host "NX PID: $($nx.Id)"
Write-Host "UI PID: $($server.Id)"
Write-Host "Assistant: $url"
Write-Host "Backend: $Backend"
Write-Host "Load journal: Tools > Journal > Play > $repo\nx_bridge\BranchCSmokeJournal.cs"
Write-Host "Close this PowerShell window to stop the UI server."
Wait-Process -Id $server.Id
