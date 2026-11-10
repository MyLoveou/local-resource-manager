<#
.SYNOPSIS
    spec-check — 校验本仓的结构契约（三平台一致、规则正文、计数、链接、JSON、目录纯度）。

.DESCRIPTION
    把 README / AGENTS / spec-runtime-maintain 里的人工契约变成可执行判据：

      1. 三个平台目录（.cursor / .opencode / .dsh）的资产集合一致：
         规则同名、Agent 同名、Skill 同名、workflows / evals 同名
      2. 同一 Skill 的三份 SKILL.md 逐字一致（换行归一后）
      3. 同一规则：.mdc 去掉 frontmatter 后 == .md
      4. frontmatter 合法：Skill 的 name 必须等于目录名且有 description；
         .mdc 有 description
      5. 正文平台中立：不出现 .cursor/ .opencode/ .dsh/ 前缀
         （spec-runtime-maintain 例外：它必须写平台目录）
      6. 相对链接全部可达；.speccheck.json 里的 ignoreLinkPaths 只降级为警告
      7. JSON 均可解析；opencode.json 的 instructions 文件都存在
      8. 文档里声明的数量（N 条规则 / N 个 Agent / N 个 Skill）与实物一致
      9. 平台目录里没有多余顶层条目

    退出码：0 通过（可带警告）；1 有错误。

.PARAMETER Root
    仓库根，默认取 git 根。

.PARAMETER StrictLinks
    把「被 ignoreLinkPaths 放过的坏链」也算错误。

.PARAMETER Quiet
    只输出结论行。

.EXAMPLE
    .\check-spec.ps1

.EXAMPLE
    .\check-spec.ps1 -Root D:\Project\agent-runtime-spec
#>
[CmdletBinding()]
param(
    [string]$Root = '',

    [switch]$StrictLinks,

    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

if ([string]::IsNullOrWhiteSpace($Root)) {
    $gitRoot = (& git rev-parse --show-toplevel 2>$null) -join ''
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($gitRoot)) {
        $Root = $gitRoot
    }
    else {
        $Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
    }
}
$Root = (Resolve-Path -LiteralPath $Root).Path

$script:Errors   = New-Object System.Collections.ArrayList
$script:Warnings = New-Object System.Collections.ArrayList

function Add-Error   { param([string]$M) $script:Errors.Add($M) | Out-Null }
function Add-Warning { param([string]$M) $script:Warnings.Add($M) | Out-Null }

function Get-Norm {
    param([string]$Path)
    return ((Get-Content -LiteralPath $Path -Raw -Encoding UTF8) -replace "`r`n", "`n")
}

function Remove-Frontmatter {
    param([string]$Text)
    if ($Text -match '(?s)^---\n.*?\n---\n?') { return ($Text -replace '(?s)^---\n.*?\n---\n?', '') }
    return $Text
}

function Get-Rel {
    param([string]$Full)
    return ($Full.Substring($Root.Length).TrimStart('\', '/') -replace '\\', '/')
}

function Get-DirNames {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    return @(Get-ChildItem -LiteralPath $Path -Directory | ForEach-Object { $_.Name } | Sort-Object)
}

function Get-FileNames {
    param([string]$Path, [string]$Filter = '*')
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    return @(Get-ChildItem -LiteralPath $Path -File -Filter $Filter | ForEach-Object { $_.BaseName } | Sort-Object)
}

# ---------- 配置 ----------
$ignoreLinks = @()
$cfgPath = Join-Path $Root '.speccheck.json'
if (Test-Path -LiteralPath $cfgPath) {
    try {
        $cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.ignoreLinkPaths) { $ignoreLinks = @($cfg.ignoreLinkPaths) }
    }
    catch { Add-Error ".speccheck.json 解析失败：$($_.Exception.Message)" }
}

$prefixAllow = @('skills/spec-runtime-maintain/SKILL.md')

# ---------- 1. 资产集合 ----------
$ruleCur = Get-FileNames (Join-Path $Root '.cursor/rules') '*.mdc'
$ruleOc  = Get-FileNames (Join-Path $Root '.opencode/rules') '*.md'
$agentCur = Get-FileNames (Join-Path $Root '.cursor/agents') '*.md'
$agentOc  = Get-FileNames (Join-Path $Root '.opencode/agent') '*.md'
$skillCur = Get-DirNames (Join-Path $Root '.cursor/skills')
$skillOc  = Get-DirNames (Join-Path $Root '.opencode/skills')
$skillDsh = Get-DirNames (Join-Path $Root '.dsh/skills')
$wfCur = Get-FileNames (Join-Path $Root '.cursor/workflows') '*.md'
$wfOc  = Get-FileNames (Join-Path $Root '.opencode/workflows') '*.md'
$evCur = Get-FileNames (Join-Path $Root '.cursor/evals')
$evOc  = Get-FileNames (Join-Path $Root '.opencode/evals')

function Compare-Sets {
    param([string]$Label, [string[]]$A, [string[]]$B)
    $onlyA = @($A | Where-Object { $B -notcontains $_ })
    $onlyB = @($B | Where-Object { $A -notcontains $_ })
    if ($onlyA.Count -gt 0) { Add-Error "$Label：只有左侧有 [$($onlyA -join ', ')]" }
    if ($onlyB.Count -gt 0) { Add-Error "$Label：只有右侧有 [$($onlyB -join ', ')]" }
}

Compare-Sets '规则集合 .cursor/.opencode' $ruleCur $ruleOc
Compare-Sets 'Agent 集合 .cursor/.opencode' $agentCur $agentOc
Compare-Sets 'Skill 集合 .cursor/.opencode' $skillCur $skillOc
Compare-Sets 'Skill 集合 .cursor/.dsh' $skillCur $skillDsh
Compare-Sets 'workflows 集合' $wfCur $wfOc
Compare-Sets 'evals 集合' $evCur $evOc

# ---------- 2. Skill 三份一致 + frontmatter ----------
foreach ($name in $skillCur) {
    $cursorRoot = Join-Path $Root ".cursor/skills/$name"
    $cursorSkl = Join-Path $cursorRoot 'SKILL.md'
    if (-not (Test-Path -LiteralPath $cursorSkl)) {
        Add-Error "Skill $name：缺 SKILL.md"
        continue
    }

    # 目录内所有文件（含 references/ scripts/）都要三份一致
    $relFiles = @(Get-ChildItem -LiteralPath $cursorRoot -Recurse -File | ForEach-Object {
        $_.FullName.Substring($cursorRoot.Length).TrimStart('\', '/') -replace '\\', '/'
    } | Sort-Object)

    foreach ($rel in $relFiles) {
        $baseText = Get-Norm (Join-Path $cursorRoot $rel)
        foreach ($plat in '.opencode', '.dsh') {
            $other = Join-Path $Root "$plat/skills/$name/$rel"
            if (-not (Test-Path -LiteralPath $other)) { Add-Error "Skill $name：$plat 缺 $rel"; continue }
            if ((Get-Norm $other) -ne $baseText) { Add-Error "Skill $name：$rel 在 $plat 侧不一致" }
        }
    }

    foreach ($plat in '.opencode', '.dsh') {
        $proot = Join-Path $Root "$plat/skills/$name"
        if (-not (Test-Path -LiteralPath $proot)) { continue }
        foreach ($pf in Get-ChildItem -LiteralPath $proot -Recurse -File) {
            $rel = $pf.FullName.Substring($proot.Length).TrimStart('\', '/') -replace '\\', '/'
            if ($relFiles -notcontains $rel) { Add-Error "Skill $name：$plat 多出 $rel" }
        }
    }

    $t = Get-Norm $cursorSkl
    if ($t -notmatch '(?s)^---\n(.*?)\n---') {
        Add-Error "Skill $name：缺 frontmatter"
        continue
    }
    $fm = $Matches[1]
    if ($fm -notmatch '(?m)^name:\s*(\S+)') { Add-Error "Skill $name：frontmatter 缺 name" }
    elseif ($Matches[1] -ne $name) { Add-Error "Skill $name：frontmatter name=$($Matches[1]) 与目录名不一致" }
    if ($fm -notmatch '(?m)^description:') { Add-Error "Skill $name：frontmatter 缺 description" }

    if (($prefixAllow -notcontains "skills/$name/SKILL.md") -and ($t -match '\.(cursor|opencode|dsh)/')) {
        Add-Error "Skill $name：正文出现平台前缀（硬规则 2）"
    }
}

# ---------- 3. 规则正文一致 + frontmatter ----------
foreach ($name in $ruleCur) {
    $mdc = Join-Path $Root ".cursor/rules/$name.mdc"
    $md  = Join-Path $Root ".opencode/rules/$name.md"
    if (-not (Test-Path -LiteralPath $md)) { continue }

    $tMdc = Get-Norm $mdc
    $tMd  = Get-Norm $md
    if ($tMdc -notmatch '(?s)^---\n(.*?)\n---') {
        Add-Error "规则 $name：.mdc 缺 frontmatter"
    }
    elseif ($Matches[1] -notmatch '(?m)^description:') {
        Add-Error "规则 $name：.mdc frontmatter 缺 description"
    }

    $bodyMdc = (Remove-Frontmatter $tMdc).Trim()
    $bodyMd  = $tMd.Trim()
    if ($bodyMdc -ne $bodyMd) {
        Add-Error "规则 $name：.mdc 去 frontmatter 后与 .md 不一致"
    }
    if (($prefixAllow -notcontains "rules/$name.md") -and ($bodyMdc -match '\.(cursor|opencode|dsh)/')) {
        Add-Error "规则 $name：正文出现平台前缀（硬规则 2）"
    }
}

# ---------- 4. 相对链接 ----------
$linkFiles = @()
foreach ($dir in @('', '.cursor', '.opencode', '.dsh', 'docs', 'projects')) {
    $base = if ($dir -eq '') { $Root } else { Join-Path $Root $dir }
    if (-not (Test-Path -LiteralPath $base)) { continue }
    $linkFiles += Get-ChildItem -LiteralPath $base -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -eq '.md' -or $_.Extension -eq '.mdc' } |
        Where-Object {
            $rp = $_.FullName
            if ($rp.Length -gt $Root.Length) { $rp = $rp.Substring($Root.Length) }
            $rp = $rp.TrimStart('\', '/') -replace '\\', '/'
            ($rp -notmatch '^(\.git|temp|node_modules)(/|$)') -and ($rp -notmatch '/(\.git|temp|node_modules)(/|$)')
        }
}
$linkFiles = @($linkFiles | Sort-Object FullName -Unique)

foreach ($f in $linkFiles) {
    $rel = Get-Rel $f.FullName
    $text = Get-Norm $f.FullName
    $text = [regex]::Replace($text, '(?s)```.*?```', '')
    $text = [regex]::Replace($text, '`[^`\n]*`', '')
    foreach ($m in [regex]::Matches($text, '\]\(([^)#][^)]*)\)')) {
        $target = $m.Groups[1].Value.Trim()
        if ($target -match '^(https?:|mailto:|#)') { continue }
        if ($target -match '[<>|*?"]') { continue }
        $target = $target -replace '\s+"[^"]*"$', ''
        $resolved = Join-Path $f.DirectoryName $target
        if (Test-Path -LiteralPath $resolved) { continue }

        $ignored = $false
        foreach ($p in $ignoreLinks) {
            if ($rel -like ($p -replace '\\', '/')) { $ignored = $true; break }
        }
        $msg = "坏链 $rel -> $target"
        if ($ignored) {
            if ($StrictLinks) { Add-Error $msg } else { Add-Warning $msg }
        }
        else { Add-Error $msg }
    }
}

# ---------- 4b. 文档不写本机绝对路径 ----------
foreach ($f in $linkFiles) {
    $rel = Get-Rel $f.FullName
    $text = Get-Norm $f.FullName
    $hit = [regex]::Match($text, '[A-Za-z]:\\')
    if ($hit.Success) {
        $lineNo = ($text.Substring(0, $hit.Index) -split "`n").Count
        Add-Error "本机绝对路径 $rel`:$lineNo（文档里请写相对路径或「仓外」）"
    }
}
# ---------- 5. JSON 与 opencode 指令 ----------
$jsonFiles = @()
foreach ($dir in @('.cursor', '.opencode', '.dsh')) {
    $base = if ($dir -eq '') { $Root } else { Join-Path $Root $dir }
    if (-not (Test-Path -LiteralPath $base)) { continue }
    $jsonFiles += Get-ChildItem -LiteralPath $base -Recurse -File -Filter '*.json' -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName.Replace($Root, '') -notmatch '[\\/]node_modules[\\/]' }
}
foreach ($j in $jsonFiles) {
    try { Get-Content -LiteralPath $j.FullName -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null }
    catch { Add-Error "JSON 解析失败 $(Get-Rel $j.FullName)：$($_.Exception.Message)" }
}

$ocPath = Join-Path $Root '.opencode/opencode.json'
if (Test-Path -LiteralPath $ocPath) {
    $oc = Get-Content -LiteralPath $ocPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($i in @($oc.instructions)) {
        if ([string]::IsNullOrWhiteSpace($i)) { continue }
        if (-not (Test-Path -LiteralPath (Join-Path $Root $i))) { Add-Error "opencode.json 的 instructions 指向不存在的文件：$i" }
    }
    if ($oc.mcp) {
        $mcpNames = @($oc.mcp.PSObject.Properties.Name)
        foreach ($n in $mcpNames) {
            if ([string]::IsNullOrWhiteSpace($n)) { Add-Error 'opencode.json 的 mcp 有空的 key' }
        }
    }
}

# ---------- 6. 文档声明的数量 ----------
$actual = @{
    rules    = $ruleCur.Count
    agents   = $agentCur.Count
    skills   = $skillCur.Count
}

$claimFiles = @(
    'README.md', 'STRUCTURE.md', 'AGENTS.md', 'docs/product/facts.md'
)
$claimPatterns = @(
    @{ re = 'rules/\*\.mdc\s+(\d+)';            kind = 'rules' },
    @{ re = 'agents/\*\.md\s+(\d+)';            kind = 'agents' },
    @{ re = 'skills/<name>/\s+(\d+)';           kind = 'skills' },
    @{ re = 'skills/<name>/SKILL\.md\s+(\d+)';  kind = 'skills' },
    @{ re = '(\d+)\s*条规则';                   kind = 'rules' },
    @{ re = '(\d+)\s*个\s*Agent';               kind = 'agents' },
    @{ re = '(\d+)\s*个\s*Skill';               kind = 'skills' }
)

foreach ($cf in $claimFiles) {
    $p = Join-Path $Root $cf
    if (-not (Test-Path -LiteralPath $p)) { continue }
    $text = Get-Norm $p
    foreach ($cp in $claimPatterns) {
        foreach ($m in [regex]::Matches($text, $cp.re)) {
            $n = [int]$m.Groups[1].Value
            if ($n -ne $actual[$cp.kind]) {
                Add-Error "文档计数漂移 $cf：写的是 $n，实际 $($actual[$cp.kind])（$($cp.kind)）"
            }
        }
    }
}

# ---------- 6b. 规则分类计数 ----------
$groups = @{}
foreach ($n in $ruleCur) {
    $prefix = ($n -split '-')[0]
    if (-not $groups.ContainsKey($prefix)) { $groups[$prefix] = 0 }
    $groups[$prefix] = $groups[$prefix] + 1
}
$knownGroups = @('common', 'java', 'react', 'vue', 'typescript')
$knownSum = 0
foreach ($g in $knownGroups) { if ($groups.ContainsKey($g)) { $knownSum += $groups[$g] } }
$otherCount = $ruleCur.Count - $knownSum

$structurePath = Join-Path $Root 'STRUCTURE.md'
if (Test-Path -LiteralPath $structurePath) {
    $st = Get-Norm $structurePath
    $m = [regex]::Match($st, 'common (\d+) / java (\d+) / react (\d+) / vue (\d+) / typescript (\d+) / 其它 (\d+)')
    if ($m.Success) {
        $pairs = @(
            @{ name = 'common';     doc = [int]$m.Groups[1].Value },
            @{ name = 'java';       doc = [int]$m.Groups[2].Value },
            @{ name = 'react';      doc = [int]$m.Groups[3].Value },
            @{ name = 'vue';        doc = [int]$m.Groups[4].Value },
            @{ name = 'typescript'; doc = [int]$m.Groups[5].Value }
        )
        foreach ($p in $pairs) {
            $key = $p.name
            $real = 0
            if ($groups.ContainsKey($key)) { $real = $groups[$key] }
            if ($p.doc -ne $real) { Add-Error "STRUCTURE 规则分类漂移：$key 写 $($p.doc)，实际 $real" }
        }
        if ($otherCount -ne [int]$m.Groups[6].Value) {
            Add-Error "STRUCTURE 规则分类漂移：其它 写 $($m.Groups[6].Value)，实际 $otherCount"
        }
    }
}
# ---------- 7. 平台目录纯度 ----------
$layout = @{
    '.cursor'   = @('rules', 'agents', 'skills', 'workflows', 'evals', 'hooks', 'mcp', 'mcp.json', 'constraints.md')
    '.opencode' = @('rules', 'agent', 'skills', 'workflows', 'evals', 'mcp', 'opencode.json', 'constraints.md')
    '.dsh'      = @('skills', 'README.md')
}
foreach ($dir in $layout.Keys) {
    $base = if ($dir -eq '') { $Root } else { Join-Path $Root $dir }
    if (-not (Test-Path -LiteralPath $base)) { Add-Error "缺平台目录 $dir"; continue }
    foreach ($item in Get-ChildItem -LiteralPath $base -Force) {
        if ($layout[$dir] -notcontains $item.Name) { Add-Warning "平台目录 $dir 有多余条目：$($item.Name)" }
    }
}

# ---------- 8. 项目装配单 ----------
$projRoot = Join-Path $Root 'projects'
if (Test-Path -LiteralPath $projRoot) {
    $validPlatforms = @('cursor', 'opencode', 'dsh')

    foreach ($pd in Get-ChildItem -LiteralPath $projRoot -Directory | Where-Object { $_.Name -notlike '_*' }) {
        $pname = $pd.Name
        $asmPath = Join-Path $pd.FullName 'assembly.json'
        if (-not (Test-Path -LiteralPath $asmPath)) { Add-Error "projects/$pname：缺 assembly.json"; continue }
        if (-not (Test-Path -LiteralPath (Join-Path $pd.FullName 'README.md'))) { Add-Error "projects/$pname：缺 README.md" }

        try { $asm = Get-Content -LiteralPath $asmPath -Raw -Encoding UTF8 | ConvertFrom-Json }
        catch { Add-Error "projects/$pname/assembly.json 解析失败：$($_.Exception.Message)"; continue }

        if ($asm.project -ne $pname) { Add-Error "projects/$pname：project 字段是 '$($asm.project)'，应与目录名一致" }

        foreach ($pl in @($asm.platforms)) {
            if ($validPlatforms -notcontains $pl) { Add-Error "projects/$pname：platforms 里的 '$pl' 不合法" }
        }

        $inc = @()
        foreach ($pat in @($asm.rules.include)) {
            if ([string]::IsNullOrWhiteSpace($pat)) { continue }
            $hits = @($ruleCur | Where-Object { $_ -like $pat })
            if ($hits.Count -eq 0) { Add-Error "projects/$pname：规则通配 '$pat' 展开为空" }
            $inc += $hits
        }
        $exc = @()
        foreach ($pat in @($asm.rules.exclude)) {
            if ([string]::IsNullOrWhiteSpace($pat)) { continue }
            $exc += @($ruleCur | Where-Object { $_ -like $pat })
        }
        foreach ($n in $inc) {
            if ($exc -contains $n) { Add-Error "projects/$pname：规则 '$n' 同时出现在 include 与 exclude" }
        }

        foreach ($s in @($asm.skills)) {
            if ([string]::IsNullOrWhiteSpace($s)) { continue }
            if ($skillCur -notcontains $s) { Add-Error "projects/$pname：Skill '$s' 不存在" }
        }
        if (@($asm.skills) -notcontains 'learning-notes') {
            Add-Error "projects/$pname：缺必装 Skill 'learning-notes'（交付后的经验总结）"
        }
        foreach ($a in @($asm.agents)) {
            if ([string]::IsNullOrWhiteSpace($a)) { continue }
            if ($agentCur -notcontains $a) { Add-Error "projects/$pname：Agent '$a' 不存在" }
        }
    }
}
# ---------- 输出 ----------
if (-not $Quiet) {
    Write-Host ''
    foreach ($w in $script:Warnings) { Write-Host "  ! $w" -ForegroundColor Yellow }
    foreach ($e in $script:Errors)   { Write-Host "  x $e" -ForegroundColor Red }
}

if ($script:Errors.Count -gt 0) {
    Write-Host "spec-check  failed  错误 $($script:Errors.Count)，警告 $($script:Warnings.Count)（规则 $($actual.rules) / Agent $($actual.agents) / Skill $($actual.skills)）" -ForegroundColor Red
    exit 1
}

Write-Host "spec-check  ok  规则 $($actual.rules) / Agent $($actual.agents) / Skill $($actual.skills)，警告 $($script:Warnings.Count)" -ForegroundColor Green
exit 0
