# 22 · 踩坑：pnpm 硬链接的 ACL 让 CLI 起不来

> 触发场景：把 OpenSpec CLI 装进仓库后，`openspec` 一执行就报「找不到包」。
> 关联：与 [11-踩坑-pnpm11构建脚本拦截](11-踩坑-pnpm11构建脚本拦截.md)、[13-踩坑-网络镜像](13-踩坑-网络镜像.md) 同属「依赖装好了但跑不起来」。

## 现象

```text
Error: Cannot find package 'D:\Project\资源管理器\node_modules\.pnpm\ora@9.4.1\node_modules\chalk\index.js'
    at legacyMainResolve (...)
  code: 'ERR_MODULE_NOT_FOUND'
```

而该目录**明明存在**：`chalk/source/index.js`、`package.json` 都在。

## 根因

pnpm 默认从内容寻址存储（本次为 `D:\.pnpm-store\v11`）**硬链接**到 `node_modules`。该 `chalk` 文件的 ACL 不含沙箱用户组，于是：

1. 沙箱内读取 `chalk/package.json` → **拒绝访问**；
2. Node 读不到 `exports` 字段，退化成 legacy `main` 解析；
3. 找不到 `index.js` → 报「包不存在」。

**报错说「找不到」，实际是「读不了」。**

## 排查手法

```powershell
# 1) 先看是「不存在」还是「读不了」
$f = 'node_modules\.pnpm\chalk@5.6.2\node_modules\chalk\package.json'
Test-Path $f                                        # True → 文件在
[IO.File]::ReadAllBytes((Resolve-Path $f))          # 抛 Access denied → 是权限

# 2) 对比一个正常包的 ACL，正常会列出沙箱用户组
icacls (Resolve-Path $f)
icacls "node_modules\.pnpm\vue@*\node_modules\vue\package.json"
```

正常的文件能看到类似 `DESKTOP-XXXX\CodexSandboxUsers:(I)(M)` 的 ACE。

## 修复

```powershell
# 让 pnpm 复制而不是硬链接，复制进工作区的文件会继承正常 ACL
Remove-Item -LiteralPath 'node_modules\.pnpm\lock.yaml' -Force
pnpm install --package-import-method=copy
```

验证：`.node_modules\.bin\openspec.CMD --version` 能打印版本号。

## 三个附带坑

1. **`pnpm install` 会说「Already up to date」而不重链**。必须删掉生成文件 `node_modules/.pnpm/lock.yaml`（以及可选的 `node_modules/.pnpm-workspace-state-v1.json`）再装。
2. **`pnpm install --force` 不一定重链**，本次它对缺失包仍然跳过。
3. **别用 `pnpm store prune` 来修这个**：它会连带清掉大量未被引用的缓存（本次删了 767 个包 / 1.49 GB，耗时数分钟），且不解决 ACL。

## 教训

1. 依赖「装好了」但 CLI 起不来，先查**权限/ACL**，别先怀疑代码或包版本。
2. `Cannot find package` 不等于文件不存在；Node 的 legacy 解析会把 EACCES 伪装成 NOT_FOUND。
3. 修 `node_modules` 状态类问题，优先删 pnpm 的**状态文件**（`.pnpm/lock.yaml`）而不是删包目录。

## 二次坑：copy 模式重装后 Electron 二进制没下载

`pnpm install --package-import-method=copy` 之后只有 `esbuild` 的 postinstall 跑了，**Electron 的 postinstall 被跳过**，于是 `pnpm dev` 直接失败：

```text
Error: Electron uninstall
    at getElectronPath (.../electron-vite/dist/chunks/lib-*.js:155:19)
```

确诊方法（`electron` 包文件齐全，但缺 `path.txt` 与 `dist/`）：

```powershell
Get-ChildItem apps\desktop\node_modules\electron | Select-Object Name
Test-Path apps\desktop\node_modules\electron\path.txt   # False 即为本坑
```

修复（走本项目验证过的 npmmirror 镜像，见 [13-踩坑-网络镜像](13-踩坑-网络镜像.md)）：

```powershell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
node apps/desktop/node_modules/electron/install.js
# 或： pnpm rebuild electron
```

完成后确认 `path.txt` 与 `dist/electron.exe` 出现，再 `pnpm dev`。

### 教训（追加）

4. 动过 `node_modules` 的重装之后，**必须复核「需要 postinstall 下二进制的包」**：Electron、esbuild 这类包，包文件在 ≠ 二进制在。

## 本仓工具链 CLI（装在哪、怎么调）

| 工具 | 安装位置 | 调用 |
|------|----------|------|
| OpenSpec | 仓库根 devDependency（`@fission-ai/openspec`） | `pnpm exec openspec list` / `pnpm openspec list` |
| CodeGraph | 全局 npm（`@colbymchenry/codegraph`，另有 MCP 注册） | `codegraph index .` / `codegraph explore "<问题>"` / MCP `codegraph_explore` |

CodeGraph 的 MCP 已注册进 `~/.codex/config.toml`（`codegraph serve --mcp`），**需重启会话**才会出现 `codegraph_*` 工具；未出现时用 shell 版 `codegraph explore` 等价替代。

## 扩展阅读

- [11-踩坑-pnpm11构建脚本拦截](11-踩坑-pnpm11构建脚本拦截.md)
- [29-踩坑-测试依赖本机环境](29-踩坑-测试依赖本机环境.md)
