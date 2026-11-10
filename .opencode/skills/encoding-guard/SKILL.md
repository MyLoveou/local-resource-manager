---
name: encoding-guard
description: >-
  提交前编码校验：挡住问号替字（???）、U+FFFD 替换符、GBK 混入、mojibake、坏掉的仓库描述。
  校验不通过就不让 commit / push。
  触发：提交前、push 前、中文变问号、乱码、mojibake、编码校验、仓库描述是问号。
---

# 编码守卫

## 何时用

- `git commit` / `git push` 之前（装成钩子后自动跑，不用手点）
- 页面上看到 `???`、`�`、`锟斤拷` 这类字
- 新建仓库、批量导入老项目、给仓库改描述之后
- 交付前自检（与 `verification-gate` 一起用）

## 为什么会变成问号

非 ASCII 字符走进「不支持 UTF-8 的通道」时，编码器会把它替换成 `?`；**替换不可逆**，原字已经丢了，没法靠命令还原。常见来源：

| 来源 | 后果 |
|------|------|
| `cmd /c "..."`、`powershell -Command "..."` 传中文参数 | 参数变 `?` |
| `gh repo create --description 中文`、API body 按 ANSI 序列化 | 仓库描述变 `?` |
| `Set-Content` / `Out-File` 不写 `-Encoding utf8` | 文件变 GBK，或直接 `?` |
| 编辑器 / 终端以 GBK（936）、OEM（437）处理 | 混合乱码 |
| 经过非 UTF-8 剪贴板或控制台重定向 | 零散 `?` |

本机终端默认代码页可能是 437 或 936，用 PowerShell 传中文最容易踩。

## 判定规则

| 级别 | 条件 |
|------|------|
| 拦 | 文本里出现 U+FFFD 替换符 |
| 拦 | 同一行既有中文又有连续 `???`（≥3） |
| 拦 | 任意位置连续问号 ≥4 |
| 拦 | 典型 mojibake 片段：`锟斤拷`、`ï¿½`、`Ã¤`、`â€™` 等 |
| 拦 | 提交信息、文件名命中以上任意一条 |
| 告警 | 文件不是合法 UTF-8（老项目 GBK 源码属正常；`-Strict` 才拦） |

二进制（含 NUL 字节）跳过；超过 5 MB 跳过；只查本次提交 / 待推送范围，不回溯历史。

## 手动校验

```powershell
$g = 'skills/encoding-guard/scripts/check-encoding.ps1'

& $g -Mode commit            # 暂存区 + 正在写的提交信息
& $g -Mode push              # 未推送的提交信息与改动
& $g -Mode files -Path .     # 整棵树
& $g -Mode remote            # 当前仓库在 GitHub 上的描述
& $g -Mode files -Path . -Strict   # 非 UTF-8 也算失败
```

退出码：`0` 通过，`1` 未通过。加 `-Quiet` 只看结果不打印细节。

## 装成钩子（不通过就挡住）

```powershell
$i = 'skills/encoding-guard/scripts/install-hooks.ps1'

& $i                        # 只装当前仓库：pre-commit + pre-push
& $i -Scope global          # 所有仓库：~/.githooks + core.hooksPath（链式调用仓库自带钩子）
& $i -Uninstall             # 卸当前仓库
& $i -Scope global -Uninstall   # 卸全局并清 core.hooksPath
```

钩子优先用 `pwsh`，没有就退回 `powershell`；两个都没有则打印提示并放行（不静默失败）。

## 失败怎么修

- 文件里的 `???` / `�`：原文已丢，对照前一版或原稿重写该行

```powershell
git show HEAD:path/to/file   # 看上一版这一行长什么样
```

- 提交信息坏了且未推送：`git commit --amend -m "<正确内容>"`；已推送只能 `git revert` 或改写历史
- 仓库描述坏了：用 UTF-8 字节体重写，别让工具自己序列化

```powershell
$cred  = "protocol=https`nhost=github.com`n" | git credential fill
$tok   = ($cred | Select-String '^password=').ToString().Substring(9)
$body  = @{ description = '中文描述'; homepage = '' } | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
Invoke-RestMethod -Method Patch -Uri 'https://api.github.com/repos/<owner>/<repo>' `
  -Headers @{ Authorization = "Bearer $tok"; 'User-Agent' = 'encoding-guard' } `
  -ContentType 'application/json; charset=utf-8' -Body $bytes
```

## 写中文的安全做法

- 文件用 `-Encoding utf8`（Windows PowerShell 5.1 用 `utf8BOM`；Node / Python 默认就是 UTF-8）
- 提交信息走 `git commit -F <utf8 文件>` 或 `-m`，不要经过 `cmd /c`
- 调 API 时先把 body 转成 UTF-8 字节，`Content-Type` 带 `charset=utf-8`
- 跨进程传中文时写成文件再读，别塞进命令行参数
- 脚本里出现中文时，`.ps1` 存成 UTF-8 **带 BOM**，否则 5.1 会按 ANSI 读

## 豁免

文档里需要故意展示坏字（比如本 Skill 自己）时，在仓库根放 `.encodingignore`，一行一个通配：

```
**/encoding-guard/**
examples/mojibake/**
```

## 边界

- 不自动修复：丢字无法还原，只做拦截与定位
- 不查远程 README 渲染、issue、PR 正文
- `-Mode remote` 依赖本机已有 GitHub 凭据（`git credential fill` 能取到）
- 只覆盖 PowerShell 侧；Linux / macOS 上需要自备等效脚本（规则同上）
