<#
.SYNOPSIS
    spec-check 的自测：先造一份"健康副本"，再逐项破坏，确认校验器都能拦住。

.DESCRIPTION
    校验器本身也会漂移（误报、漏报）。这个脚本把"它应该失败"的场景写成断言：

      1. 健康副本           -> 期望通过（0）
      2. 改坏 .dsh 侧 Skill -> 期望失败（1）
      3. 改错规则分类计数   -> 期望失败（1）
      4. 塞一个坏链         -> 期望失败（1）
      5. 塞一个盘符绝对路径 -> 期望失败（1）
      6. 装配单引用不存在的 Skill -> 期望失败（1）

    任何一条断言不符，本脚本退出码 1。CI 每次都会跑它。

.PARAMETER Root
    被测仓库根，默认取 git 根。
#>
[CmdletBinding()]
param(
    [string]$Root = ''
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

if ([string]::IsNullOrWhiteSpace($Root)) {
    $gitRoot = (& git rev-parse --show-toplevel 2>$null) -join ''
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($gitRoot)) { $Root = $gitRoot }
    else { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path }
}
$Root = (Resolve-Path -LiteralPath $Root).Path

$checker = Join-Path $PSScriptRoot 'check-spec.ps1'
if (-not (Test-Path -LiteralPath $checker)) { Write-Host "找不到 check-spec.ps1" -ForegroundColor Red; exit 1 }

$script:Pass = 0
$script:Fail = 0

function Assert-Exit {
    param([string]$Label, [int]$Expected, [int]$Actual)
    if ($Expected -eq $Actual) {
        $script:Pass++
        Write-Host "  ok   $Label（退出码 $Actual）" -ForegroundColor Green
    }
    else {
        $script:Fail++
        Write-Host "  FAIL $Label：期望 $Expected，实际 $Actual" -ForegroundColor Red
    }
}

function Copy-RepoTree {
    param([string]$Source, [string]$Dest)
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    $skip = @('.git', 'temp', 'node_modules')
    Get-ChildItem -LiteralPath $Source -Force | Where-Object { $skip -notcontains $_.Name } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Dest -Recurse -Force
    }
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('spec-check-selftest-' + [guid]::NewGuid().ToString('N'))
Copy-RepoTree -Source $Root -Dest $tmp

try {
    & $checker -Root $tmp -Quiet | Out-Null
    Assert-Exit '健康副本应通过' 0 $LASTEXITCODE

    # 2. 破坏 .dsh 侧 Skill
    $victim = Join-Path $tmp '.dsh/skills/spec-check/SKILL.md'
    $backup = [System.IO.File]::ReadAllText($victim)
    [System.IO.File]::AppendAllText($victim, "`n多出来的一行`n", (New-Object System.Text.UTF8Encoding($false)))
    & $checker -Root $tmp -Quiet | Out-Null
    Assert-Exit 'Skill 三份不一致应被拦住' 1 $LASTEXITCODE
    [System.IO.File]::WriteAllText($victim, $backup, (New-Object System.Text.UTF8Encoding($false)))

    # 3. 破坏规则分类计数
    $struct = Join-Path $tmp 'STRUCTURE.md'
    $backup = [System.IO.File]::ReadAllText($struct)
    [System.IO.File]::WriteAllText($struct, ($backup -replace 'common \d+', 'common 99'), (New-Object System.Text.UTF8Encoding($false)))
    & $checker -Root $tmp -Quiet | Out-Null
    Assert-Exit '规则分类漂移应被拦住' 1 $LASTEXITCODE
    [System.IO.File]::WriteAllText($struct, $backup, (New-Object System.Text.UTF8Encoding($false)))

    # 4. 塞坏链
    $readme = Join-Path $tmp 'README.md'
    $backup = [System.IO.File]::ReadAllText($readme)
    [System.IO.File]::AppendAllText($readme, "`n[x](./no-such-file.md)`n", (New-Object System.Text.UTF8Encoding($false)))
    & $checker -Root $tmp -Quiet | Out-Null
    Assert-Exit '坏链应被拦住' 1 $LASTEXITCODE
    [System.IO.File]::WriteAllText($readme, $backup, (New-Object System.Text.UTF8Encoding($false)))

    # 5. 塞盘符路径
    [System.IO.File]::AppendAllText($readme, "`n示例：D:\demo\path`n", (New-Object System.Text.UTF8Encoding($false)))
    & $checker -Root $tmp -Quiet | Out-Null
    Assert-Exit '本机绝对路径应被拦住' 1 $LASTEXITCODE
    [System.IO.File]::WriteAllText($readme, $backup, (New-Object System.Text.UTF8Encoding($false)))

    # 6b. 装配单缺必装 Skill（learning-notes）
    $asmDir2 = $null
    if (Test-Path -LiteralPath (Join-Path $tmp 'projects')) {
        $asmDir2 = Get-ChildItem -LiteralPath (Join-Path $tmp 'projects') -Directory | Where-Object { $_.Name -notlike '_*' } | Select-Object -First 1
    }
    if ($null -ne $asmDir2) {
        $asmFile2 = Join-Path $asmDir2.FullName 'assembly.json'
        $backup2 = [System.IO.File]::ReadAllText($asmFile2)
        $obj2 = $backup2 | ConvertFrom-Json
        $obj2.skills = @($obj2.skills | Where-Object { $_ -ne 'learning-notes' })
        [System.IO.File]::WriteAllText($asmFile2, ($obj2 | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding($false)))
        & $checker -Root $tmp -Quiet | Out-Null
        Assert-Exit '装配单缺 learning-notes 应被拦住' 1 $LASTEXITCODE
        [System.IO.File]::WriteAllText($asmFile2, $backup2, (New-Object System.Text.UTF8Encoding($false)))
    }

    # 6. 装配单引用不存在的 Skill
    $projRoot = Join-Path $tmp 'projects'
    if (Test-Path -LiteralPath $projRoot) {
        $asmDir = Get-ChildItem -LiteralPath $projRoot -Directory | Where-Object { $_.Name -notlike '_*' } | Select-Object -First 1
        if ($null -ne $asmDir) {
            $asmFile = Join-Path $asmDir.FullName 'assembly.json'
            $asmBackup = [System.IO.File]::ReadAllText($asmFile)
            $asmObj = $asmBackup | ConvertFrom-Json
            $asmObj.skills = @($asmObj.skills) + 'no-such-skill'
            [System.IO.File]::WriteAllText($asmFile, ($asmObj | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding($false)))
            & $checker -Root $tmp -Quiet | Out-Null
            Assert-Exit '装配单引用不存在的 Skill 应被拦住' 1 $LASTEXITCODE
            [System.IO.File]::WriteAllText($asmFile, $asmBackup, (New-Object System.Text.UTF8Encoding($false)))
        }
    }
}
finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ''
if ($script:Fail -gt 0) {
    Write-Host "selftest  failed  通过 $($script:Pass)，失败 $($script:Fail)" -ForegroundColor Red
    exit 1
}
Write-Host "selftest  ok  通过 $($script:Pass)/$($script:Pass)" -ForegroundColor Green
exit 0
