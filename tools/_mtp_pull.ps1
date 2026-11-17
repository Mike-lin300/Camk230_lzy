# _mtp_pull.ps1 —— 从 CanMV（MTP 便携设备）拉数据到本地，输出机读行
# 由 tools/pull_logs.py 调用；也可单独运行。
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\_mtp_pull.ps1 -Remote 'data\logs' -Dest .\logs
# 退出码: 0 成功 / 2 无设备 / 4 远端路径不存在 / 6 拷贝超时
[CmdletBinding()]
param(
    [string]$DeviceName = 'CanMV',
    [string]$Remote = 'data\logs',
    [string]$Dest,
    [string]$Only,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'

function Emit($k, $v) { Write-Output ("{0}={1}" -f $k, $v) }

function Get-ShellFolder([object]$shell, [string]$path, [int]$retry = 4) {
    for ($i = 1; $i -le $retry; $i++) {
        try { $f = $shell.NameSpace($path); if ($f) { return $f } } catch { }
        Start-Sleep -Milliseconds (300 * $i)
    }
    return $null
}

function Get-ChildFolder([object]$parentFolder, [string]$name, [int]$retry = 4) {
    for ($i = 1; $i -le $retry; $i++) {
        try {
            $item = $parentFolder.ParseName($name)
            if ($item) { $f = $item.GetFolder; if ($f) { return $f } }
        } catch { }
        Start-Sleep -Milliseconds (300 * $i)
    }
    return $null
}

$repo = Split-Path -Parent $PSScriptRoot
if (-not $Dest) { $Dest = Join-Path $repo 'logs' }
$Dest = [IO.Path]::GetFullPath($Dest)
if (-not (Test-Path -LiteralPath $Dest)) { New-Item -ItemType Directory -Force -Path $Dest | Out-Null }

$sh = New-Object -ComObject Shell.Application
$device = $sh.NameSpace(17).Items() | Where-Object { $_.Name -eq $DeviceName } | Select-Object -First 1
if (-not $device) {
    Emit 'RESULT' 'no_device'
    Emit 'DETAIL' "$DeviceName not in This PC"
    exit 2
}
Emit 'DEVICE' $device.Name

$folder = Get-ShellFolder $sh $device.Path
if (-not $folder) { Emit 'RESULT' 'no_device'; exit 2 }
foreach ($seg in ($Remote -split '[\\/]' | Where-Object { $_ })) {
    $next = Get-ChildFolder $folder $seg
    if (-not $next) {
        Emit 'RESULT' 'missing'
        Emit 'DETAIL' "/$Remote ($seg)"
        exit 4
    }
    $folder = $next
}

$items = @($folder.Items())
if ($Only) { $items = @($items | Where-Object { $_.Name -eq $Only }) }
if ($items.Count -eq 0) { Emit 'RESULT' 'empty'; exit 0 }

$destFolder = $sh.NameSpace($Dest)
$pulled = 0
$skipped = 0
foreach ($it in $items) {
    $local = Join-Path $Dest $it.Name
    if ((Test-Path -LiteralPath $local) -and (-not $Force)) {
        Emit 'SKIP' $it.Name
        $skipped++
        continue
    }
    $t0 = Get-Date
    $destFolder.CopyHere($it, 20)
    $deadline = (Get-Date).AddSeconds(120)
    $last = -1
    $stable = 0
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $local) {
            $c = @(Get-ChildItem -LiteralPath $local -Recurse -File -ErrorAction SilentlyContinue).Count
            if ($c -eq $last) { $stable++ } else { $stable = 0; $last = $c }
            if ($stable -ge 3) { break }
        }
        Start-Sleep -Milliseconds 300
    }
    if (Test-Path -LiteralPath $local) {
        $files = @(Get-ChildItem -LiteralPath $local -Recurse -File -ErrorAction SilentlyContinue)
        $bytes = ($files | Measure-Object -Property Length -Sum).Sum
        if ($null -eq $bytes) { $bytes = 0 }
        Emit 'PULLED' $it.Name
        Emit 'FILES' $files.Count
        Emit 'BYTES' ([int]$bytes)
        Emit 'MS' ([int]((Get-Date) - $t0).TotalMilliseconds)
        $pulled++
    } else {
        Emit 'TIMEOUT' $it.Name
    }
}
Emit 'DEST' $Dest
Emit 'PULLED_COUNT' $pulled
Emit 'SKIPPED_COUNT' $skipped
Emit 'RESULT' 'ok'
exit 0
