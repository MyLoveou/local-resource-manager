---
name: spec-check
description: >-
  自动校验本仓结构契约：三平台资产集合一致、Skill 三份逐字相同、规则正文相同、
  frontmatter 合法、正文无平台前缀、相对链接可达、JSON 可解析、文档数量与实物一致。
  触发：提交前、push 前、改规则 / Agent / Skill、发版、CI 红灯。
---

# 规范自检

## 为什么要有它

本仓的三条硬规则（三份副本、正文平台中立、去 frontmatter 逐字一致）与各类「N 条 / N 个」的计数，
过去只写在文档里靠人（或 AI）记着。注意力会漏：坏链、计数漂移、少改一个平台，都是这么攒出来的。
`check-spec.ps1` 把这些判据写成代码，**本地一条命令、CI 每次 push 必跑**。

## 查什么

| 判据 | 失败条件 |
|------|----------|
| 资产集合 | 规则 / Agent / Skill / workflows / evals 在三个平台目录里不同名或数量不等 |
| Skill 三份一致 | 同一 Skill 的 `SKILL.md` 三份内容（换行归一后）不完全相同 |
| 规则正文 | `.mdc` 去掉 frontmatter 后 ≠ 同名 `.md` |
| frontmatter | Skill 缺 `name` / `description`，`name` 与目录名不符；`.mdc` 缺 `description` |
| 平台中立 | 规则 / Skill 正文出现平台目录前缀（三个平台各自的目录名；`spec-runtime-maintain` 例外） |
| 相对链接 | 文档里的 `[x](./y.md)` 指向不存在的文件 |
| JSON | 平台目录里的 `.json` 解析失败；`opencode.json` 的 `instructions` 指向不存在的文件 |
| 文档计数 | README / STRUCTURE / AGENTS / facts 写的「N 条规则 / N 个 Agent / N 个 Skill」与实物不符 |
| 规则分类 | STRUCTURE 的 `common / java / react / vue / typescript / 其它` 拆分与实际不符 |
| 本机路径 | 文档里出现盘符开头的绝对路径（应写相对路径或「仓外」） |
| 目录纯度 | 平台目录顶层出现约定外的条目（只警告） |

退出码 `0` = 通过，`1` = 有错误。警告不影响退出码。

## 怎么跑

```powershell
$c = 'skills/spec-check/scripts/check-spec.ps1'
& $c                 # 校验（默认取 git 根）
& $c -Root .         # 指定仓库
& $c -StrictLinks    # 把被豁免的坏链也当错误
& $c -Quiet          # 只打结论行
```

> 脚本是 UTF-8 **带 BOM** 的 `.ps1`：Windows PowerShell 5.1 会按 ANSI 读无 BOM 文件，中文直接变乱码。

## 自测

校验器自己也会漂移（误报 / 漏报）。`selftest.ps1` 把仓库复制到临时目录，逐项制造破坏，断言每种都能被拦住：

```powershell
skills/spec-check/scripts/selftest.ps1
```

当前 6 条断言：健康副本通过、Skill 副本不一致、分类计数漂移、坏链、盘符绝对路径、装配单引用不存在的资产。CI 每次都跑；改完 `check-spec.ps1` 必须让自测全过。
## 豁免

**默认零豁免**：本仓没有豁免文件。确实需要放行时，才在仓库根建 `.speccheck.json`：

```json
{
  "ignoreLinkPaths": ["some/dir/**"]
}
```

命中的坏链降级为警告（可被 `-StrictLinks` 翻回错误）。
**豁免是暂时的**：修完就把条目删掉，整份文件没内容了就删文件。

## 接进流程

```powershell
skills/spec-check/scripts/install-hook.ps1              # 当前仓库 pre-push
skills/spec-check/scripts/install-hook.ps1 -Uninstall   # 卸载
```

CI 侧见仓根 `.github/workflows/spec-check.yml`：push / PR 自动跑 `check-spec.ps1` 与 `check-encoding.ps1`，
任一失败即红灯。本地钩子只是提前发现问题，**最终闸门在 CI**。

## 新增判据的做法

1. 判据必须是**可判定的**：能给出「哪个文件、哪条规则、期望 vs 实际」；
2. 先在真实仓库上跑一遍，确认不误报，再合入；
3. 确实需要豁免时再建 `.speccheck.json`，注明原因与到期条件，修完即删；
4. 三份副本同步（本技能自己也要过 `check-spec.ps1`）。

## 边界

- 只查结构与文本一致性，不查内容质量（规则写得对不对，靠 `code-review-gate`）；
- 不修复，只报告与阻断；
- 编码问题交给 `encoding-guard`，这里不重复。
