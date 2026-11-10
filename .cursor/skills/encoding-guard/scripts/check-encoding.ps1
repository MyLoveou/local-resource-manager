<#
.SYNOPSIS
    encoding-guard — 提交前编码校验（??? / U+FFFD / mojibake / 非 UTF-8）

.DESCRIPTION
    拦截「非 ASCII 字符被替换成 ?」这类不可逆的数据损失，以及 GBK / Latin-1 混入造成的乱码。

    直接判失败（退出码 1）：
      1. 文本出现 U+FFFD 替换符
      2. 中文行里出现连续 ???（>= 3）
      3. 任意位置连续问号 >= 4
      4. 典型 mojibake 片段：锟斤拷 / ï¿½ / Ã¤ / â€™ 等
      5. 提交信息、文件名命中以上任意一条

    只告警：文件不是合法 UTF-8（老项目 GBK 源码属正常；加 -Strict 才拦）。

.PARAMETER Mode
    commit  暂存区文件 + 正在写的提交信息（pre-commit 用）
    push    未推送提交的信息与改动（pre-push 用）
    files   指定路径整棵扫（默认当前目录）
    remote  当前仓库的 GitHub 描述（元数据坏字）

.PARAMETER Path
    -Mode files 时要扫的文件或目录。

.PARAMETER Remote
    -Mode remote 时可显式指定 owner/repo，默认从 origin 推断。

.PARAMETER Strict
    把「非 UTF-8」也当作失败。

.EXAMPLE
    .\check-encoding.ps1 -Mode commit

.EXAMPLE
    .\check-encoding.ps1 -Mode files -Path .
#>
[CmdletBinding()]
param(
    [ValidateSet('commit', 'push', 'files', 'remote')]
    [string]$Mode = 'commit',

    [string[]]$Path = @(),

    [string[]]$Remote = @(),

    [switch]$Strict,

    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

$script:Fail    = New-Object System.Collections.ArrayList
$script:Warn    = New-Object System.Collections.ArrayList
$script:Ignores = New-Object System.Collections.ArrayList
$script:Files   = 0
$script:Msgs    = 0

$script:Cjk  = '[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]'
$script:Moji = @('锟斤拷', 'ï¿½', 'Ã¤', 'Ã©', 'Ã¨', 'Ã¼', 'Ã¶', 'Ã§', 'Ã¥', 'â€', 'ã€', 'Â»', 'Â«', 'â€™')
$script:SkipDirs = '(^|[\\/])(\.git|node_modules|dist|build|\.venv|__pycache__|\.next|target)[\\/]'

function Add-Fail {
    param([string]$Message)
    $script:Fail.Add($Message) | Out-Null
}

function Add-Warn {
    param([string]$Message)
    $script:Warn.Add($Message) | Out-Null
}

function Get-NullPaths {
    param([string[]]$GitArgs)
    $out = & git @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    $text = ($out -join '')
    if ([string]::IsNullOrEmpty($text)) { return @() }
    return @($text -split "`0" | Where-Object { $_ -ne '' })
}

function Get-GitPath {
    param([string]$Name)
    $p = (& git rev-parse --git-path $Name 2>$null) -join ''
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($p)) { return $null }
    if ([System.IO.Path]::IsPathRooted($p)) { return $p }
    return (Join-Path (Get-Location).Path $p)
}

function Initialize-Ignore {
    $f = Join-Path (Get-Location).Path '.encodingignore'
    if (-not (Test-Path -LiteralPath $f)) { return }
    foreach ($line in (Get-Content -LiteralPath $f -Encoding UTF8)) {
        $t = $line.Trim()
        if ($t.Length -eq 0 -or $t.StartsWith('#')) { continue }
        $pattern = $t -replace '\*\*', '*'
        $script:Ignores.Add($pattern) | Out-Null
    }
}

function Test-Ignored {
    param([string]$Rel)
    $norm = $Rel -replace '\\', '/'
    foreach ($p in $script:Ignores) {
        if ($norm -like $p) { return $true }
    }
    return $false
}

function Test-TextBlock {
    param([string]$Label, [string]$Text)

    $lines = $Text -split "`r?`n"
    $n = 0
    foreach ($line in $lines) {
        $n++
        if ($line.Length -eq 0) { continue }

        if ($line.IndexOf([char]0xFFFD) -ge 0) {
            Add-Fail "$Label 第 $n 行含 U+FFFD 替换符"
            continue
        }

        $hit = $null
        foreach ($m in $script:Moji) {
            if ($line.IndexOf($m) -ge 0) { $hit = $m; break }
        }
        if ($null -ne $hit) {
            Add-Fail "$Label 第 $n 行含 mojibake 片段 [$hit]"
            continue
        }

        if ($line -match '\?{4,}') {
            Add-Fail "$Label 第 $n 行连续问号 >= 4（疑似丢字）"
            continue
        }
        if ($line -match '\?{3,}' -and $line -match $script:Cjk) {
            Add-Fail "$Label 第 $n 行中文里夹 ???（疑似丢字）"
        }
    }
}

function Test-FileBytes {
    param([string]$Rel, [byte[]]$Bytes)

    $script:Files++
    if ($Bytes.Length -eq 0) { return }
    if ($Bytes.Length -gt 5242880) {
        Add-Warn "$Rel 超过 5MB，跳过"
        return
    }

    $probe = [Math]::Min($Bytes.Length, 8000)
    for ($i = 0; $i -lt $probe; $i++) {
        if ($Bytes[$i] -eq 0) { return }
    }

    $enc = New-Object System.Text.UTF8Encoding($false, $true)
    try {
        $text = $enc.GetString($Bytes)
    }
    catch {
        if ($Strict) { Add-Fail "$Rel 不是合法 UTF-8（GBK / ANSI？）" }
        else { Add-Warn "$Rel 不是合法 UTF-8（GBK / ANSI？确认无误可忽略，-Strict 会拦）" }
        return
    }

    Test-TextBlock -Label $Rel -Text $text
}

function Test-FileOnDisk {
    param([string]$Rel, [string]$Root)

    if (Test-Ignored $Rel) { return }
    if ($Rel -match $script:SkipDirs) { return }

    $full = Join-Path $Root $Rel
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return }

    try { $bytes = [System.IO.File]::ReadAllBytes($full) }
    catch { Add-Warn "$Rel 读取失败，跳过"; return }

    Test-FileBytes -Rel $Rel -Bytes $bytes
}

function Test-PathName {
    param([string]$Rel)
    if ($Rel -match '\?') { Add-Fail "文件名含问号：$Rel" }
    if ($Rel.IndexOf([char]0xFFFD) -ge 0) { Add-Fail "文件名含 U+FFFD：$Rel" }
}

function Test-CommitMessageFile {
    param([string]$File)
    if (-not $File) { return }
    if (-not (Test-Path -LiteralPath $File)) { return }

    $enc = New-Object System.Text.UTF8Encoding($false, $true)
    try { $text = $enc.GetString([System.IO.File]::ReadAllBytes($File)) }
    catch { Add-Warn "提交信息不是合法 UTF-8，跳过"; return }

    $script:Msgs++
    Test-TextBlock -Label '[提交信息]' -Text $text
}

function Invoke-ModeCommit {
    $root = (Get-Location).Path
    $staged = Get-NullPaths @('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
    foreach ($f in $staged) {
        Test-PathName $f
        Test-FileOnDisk -Rel $f -Root $root
    }
    Test-CommitMessageFile (Get-GitPath 'COMMIT_EDITMSG')
}

function Invoke-ModePush {
    $root = (Get-Location).Path
    $up = (& git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>&1) -join ''
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($up)) {
        $branch = (& git rev-parse --abbrev-ref HEAD 2>$null) -join ''
        $candidate = "origin/$branch"
        & git rev-parse --verify --quiet $candidate 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $up = $candidate } else { $up = '' }
    }

    if ([string]::IsNullOrWhiteSpace($up)) {
        Add-Warn '没有可比较的上游分支，跳过提交范围，仅查暂存区'
        Invoke-ModeCommit
        return
    }

    $range = "$up..HEAD"
    $log = (& git log --format='%H%x1f%B%x1e' $range 2>$null) -join ''
    foreach ($rec in ($log -split [string][char]0x1e)) {
        $t = $rec.Trim()
        if ([string]::IsNullOrWhiteSpace($t)) { continue }
        $parts = $t -split [string][char]0x1f, 2
        $sha = $parts[0]
        if ($sha.Length -gt 7) { $sha = $sha.Substring(0, 7) }
        $script:Msgs++
        Test-TextBlock -Label "[提交 $sha]" -Text $parts[-1]
    }

    $changed = Get-NullPaths @('diff', '--name-only', '--diff-filter=ACMR', '-z', $range)
    $dirty = @()
    foreach ($f in $changed) {
        Test-PathName $f
        & git diff --quiet HEAD -- $f 2>$null
        if ($LASTEXITCODE -eq 0) { Test-FileOnDisk -Rel $f -Root $root }
        else { $dirty += $f }
    }

    # 工作区与提交不一致的文件，按提交里的内容检查，避免拿错版本
    if ($dirty.Count -gt 0) {
        $tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ('encoding-guard-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
        try {
            $zip = Join-Path $tmpDir 'blobs.zip'
            & git archive --format=zip -o $zip HEAD -- $dirty 2>$null
            if ($LASTEXITCODE -ne 0) { throw 'git archive 失败' }
            Expand-Archive -LiteralPath $zip -DestinationPath $tmpDir -Force
            foreach ($f in $dirty) {
                $blob = Join-Path $tmpDir $f
                if (Test-Path -LiteralPath $blob) {
                    Test-FileBytes -Rel $f -Bytes ([System.IO.File]::ReadAllBytes($blob))
                }
                else { Add-Warn "$f 取不到提交内容，跳过" }
            }
        }
        catch {
            foreach ($f in $dirty) { Add-Warn "$f 工作区与提交不一致，且无法读取提交内容，跳过" }
        }
        finally {
            Remove-Item -LiteralPath $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-ModeFiles {
    $root = (Get-Location).Path
    $targets = $Path
    if ($null -eq $targets -or $targets.Count -eq 0) { $targets = @('.') }

    foreach ($t in $targets) {
        if (-not (Test-Path -LiteralPath $t)) { Add-Warn "路径不存在，跳过：$t"; continue }
        $full = (Resolve-Path -LiteralPath $t).Path

        if (Test-Path -LiteralPath $full -PathType Leaf) {
            $rel = $t
            Test-PathName $rel
            Test-FileOnDisk -Rel $rel -Root (Split-Path -Parent $full)
            continue
        }

        Get-ChildItem -LiteralPath $full -Recurse -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $rel = $_.FullName
            if ($rel.Length -gt $root.Length) { $rel = $rel.Substring($root.Length) }
            $rel = $rel.TrimStart('\', '/')
            Test-PathName $rel
            Test-FileOnDisk -Rel $rel -Root $root
        }
    }
}

function Get-GitHubSlug {
    $url = (& git remote get-url origin 2>$null) -join ''
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($url)) { return $null }
    if ($url -match 'github\.com[:/](?<owner>[^/]+)/(?<repo>[^/]+?)(\.git)?/?$') {
        return "$($Matches.owner)/$($Matches.repo)"
    }
    return $null
}

function Get-GitHubToken {
    $payload = "protocol=https`nhost=github.com`n`n"
    $out = $payload | & git credential fill 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $line = $out | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
    if (-not $line) { return $null }
    return $line.Substring('password='.Length)
}

function Invoke-ModeRemote {
    $slug = $null
    if ($Remote.Count -gt 0) { $slug = $Remote[0] } else { $slug = Get-GitHubSlug }
    if ([string]::IsNullOrWhiteSpace($slug)) { Add-Fail '推断不出 GitHub 仓库，可用 -Remote owner/repo 指定'; return }

    $token = Get-GitHubToken
    if ([string]::IsNullOrWhiteSpace($token)) { Add-Fail '取不到 GitHub 凭据（git credential fill 失败）'; return }

    $headers = @{ Authorization = "Bearer $token"; 'User-Agent' = 'encoding-guard' }
    try {
        $repo = Invoke-RestMethod -Uri "https://api.github.com/repos/$slug" -Headers $headers
    }
    catch {
        Add-Fail "读取 $slug 元数据失败：$($_.Exception.Message)"
        return
    }

    if ($repo.description) {
        $script:Msgs++
        Test-TextBlock -Label "[仓库描述 $slug]" -Text $repo.description
    }
}

Initialize-Ignore

switch ($Mode) {
    'commit' { Invoke-ModeCommit }
    'push'   { Invoke-ModePush }
    'files'  { Invoke-ModeFiles }
    'remote' { Invoke-ModeRemote }
}

if (-not $Quiet) {
    Write-Host ''
    if ($script:Fail.Count -gt 0) {
        Write-Host "encoding-guard x 未通过：$($script:Fail.Count) 项（已扫描文件 $($script:Files)，文本块 $($script:Msgs)）" -ForegroundColor Red
        foreach ($m in $script:Fail) { Write-Host "  x $m" -ForegroundColor Red }
        if ($script:Warn.Count -gt 0) {
            foreach ($m in $script:Warn) { Write-Host "  ! $m" -ForegroundColor Yellow }
        }
        Write-Host '  原文已丢，无法自动还原：对照前一版（git show HEAD:<path>）或原稿重写该行。' -ForegroundColor Yellow
        Write-Host '  细节与修法：skills/encoding-guard/SKILL.md' -ForegroundColor Yellow
    }
    else {
        Write-Host "encoding-guard ok 通过（文件 $($script:Files)，文本块 $($script:Msgs)）" -ForegroundColor Green
        foreach ($m in $script:Warn) { Write-Host "  ! $m" -ForegroundColor Yellow }
    }
}

if ($script:Fail.Count -gt 0) { exit 1 }
exit 0
