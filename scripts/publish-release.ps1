param(
  [switch]$Yes,
  [switch]$Build
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$package = Get-Content -LiteralPath "apps/desktop/package.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$version = [string]$package.version
if ($version -notmatch '^\d+\.\d+\.\d+$') {
  throw "apps/desktop/package.json 的 version 不是 x.y.z：$version"
}
$tag = "v$version"
$notes = Join-Path $root "docs/releases/$tag.md"

if (-not (Test-Path -LiteralPath $notes)) {
  throw "缺少发布说明：docs/releases/$tag.md"
}

$changes = git status --porcelain
if ($changes) {
  throw "工作区不干净，请先提交或清理改动：`n$changes"
}

if (git tag --list $tag) {
  throw "本地已存在 tag $tag"
}
if (git ls-remote --tags origin "refs/tags/$tag") {
  throw "远程已存在 tag $tag"
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "master") {
  throw "当前分支是 $branch，发布只允许从 master 执行"
}

Write-Host ""
Write-Host "准备发布 $tag"
Write-Host "分支：$branch"
Write-Host "说明：docs/releases/$tag.md"
Write-Host "打包：$([bool]$Build)"
Write-Host ""

if (-not $Yes) {
  $answer = Read-Host "确认推送提交并创建 $tag？输入 y 继续"
  if ($answer -ne "y" -and $answer -ne "Y") {
    Write-Host "已取消。"
    exit 1
  }
}

if ($Build) {
  & pnpm release:win
  if ($LASTEXITCODE -ne 0) {
    throw "本地打包失败，未创建 tag"
  }
}

git push origin HEAD
if ($LASTEXITCODE -ne 0) {
  throw "推送提交失败，未创建 tag"
}

git tag $tag
if ($LASTEXITCODE -ne 0) {
  throw "创建 tag 失败"
}

git push origin $tag
if ($LASTEXITCODE -ne 0) {
  throw "推送 tag 失败；tag 已在本地创建，请检查后重试"
}

Write-Host ""
Write-Host "已触发发布：$tag"
Write-Host "GitHub Actions：https://github.com/MyLoveou/local-resource-manager/actions"
Write-Host "Release：https://github.com/MyLoveou/local-resource-manager/releases/tag/$tag"
