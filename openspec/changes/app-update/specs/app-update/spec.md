## Purpose

为 Windows 安装版提供应用内更新：启动与手动检查 GitHub Releases 上的新版本，展示更新公告，下载后在应用内重启安装；绿色 zip 仍保持手动更新。首次带 updater 的 0.1.1 需手动安装，之后版本可自动更新。

## ADDED Requirements

### Requirement: 应用内更新

系统 SHALL 在打包态通过 `electron-updater` 检查 GitHub Releases 的 `latest.yml`，发现新版本时展示版本与更新公告；用户确认后下载，下载完成可重启安装；开发态提示「仅安装版支持自动更新」。

#### Scenario: 检查与公告

- **WHEN** 安装版启动（8 秒后）或用户在设置页点「检查更新」，且存在更高版本
- **THEN** 显示新版本号与公告；无更新时显示「已是最新版本」；无 Release 时显示可读错误且不崩溃
- **对应测试**：`tests.md` T1/T2

#### Scenario: 下载与安装

- **WHEN** 用户点「下载更新」并完成下载
- **THEN** 显示进度；完成后提供「重启安装」，重启后版本变为新版本，`%APPDATA%` 数据保留
- **对应测试**：`tests.md` T3（需发布 Release 后手验）

### Requirement: 发布与版本单一来源

系统 SHALL 以 `apps/desktop/package.json` 的 `version` 为唯一版本源；CI 在 tag `v*` 时构建并创建 GitHub Release，上传安装包、blockmap、`latest.yml` 与 SHA256。

#### Scenario: 发布

- **WHEN** 推送 tag `v0.1.2`（package.json 为 0.1.2）
- **THEN** CI 产出 setup/zip/latest.yml/SHA256 并发布 Release；0.1.1 客户端可检测到
- **对应测试**：`tests.md` T4（CI 未在本环境运行）

## MODIFIED Requirements

（无）

## REMOVED Requirements

（无）
