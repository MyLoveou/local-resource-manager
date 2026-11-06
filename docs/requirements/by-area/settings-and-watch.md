# 设置与监视 · 跨类型需求

## 1. 设置

已实现：

- 抓取凭证：TMDB API key、Bangumi access token、Mikan 地址；环境变量可锁定。
- 消费渠道：每个类型可选 embedded / system / command / workbench；命令模板支持 `{path}`。
- 系统路径：库路径、日志目录、备份目录；支持备份。
- 监视目录：按类型配置源目录；事件派发、启动补扫、自动导入。
- 命名解析：解析规则、标题带集数、自动合集。
- 主题：内置主题 + 用户 CSS；分区可见性由代码配置。

未实现/待确认：

| 能力 | 状态 | 说明 |
|------|------|------|
| 设置导入/导出 | 未实现 | 无配置包 |
| 凭证加密存储 | 部分 | 明文配置交由系统账户权限；未做密钥库 |
| 监视目录排除规则 | 未实现 | 仅按类型目录，无 glob/忽略规则 |
| 代理/网络设置 | 未实现 | 走系统/环境变量 |
| 多用户/权限 | OUT | 单机应用 |

## 2. 监视目录

- 事件驱动 + 启动补扫；按资源类型派发。
- 自动导入使用 sha256 去重；anime/av 支持目录级增量挂集。
- 监视变化的 UI 刷新走 `watchRevision` 软刷新，保留滚动位置。
- 源目录只监视，不登记为可再扫的根（D-20260927-01）。

## 3. 明确边界

- 不保存第三方账号密码（只保存 API token/地址）。
- 不在设置里做下载器配置；下载委托第三方。
- 不把监视目录的任意文件都当媒体；按类型扩展名/包规则过滤。

## 4. 入口

- `apps/desktop/src/renderer/src/components/SettingsModal`
- `apps/backend/app/settings/`
- `apps/backend/app/shared/utils/watch_*`
- `features/app-settings-first/`、`features/watch-source-dirs/`
