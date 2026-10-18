/**
 * 应用更新（electron-updater）：检查 → 下载 → 重启安装。
 * 仅打包态启用；开发态返回 unsupported（可用 UPDATE_FEED_URL 联调）。
 */
import { app, BrowserWindow, ipcMain } from 'electron'
import { existsSync } from 'fs'
import { dirname, join } from 'path'
import { autoUpdater } from 'electron-updater'
import type { UpdateInfo } from 'electron-updater'
import { log } from '../../log'

export type UpdatePhase =
  | 'idle'
  | 'checking'
  | 'available'
  | 'downloading'
  | 'downloaded'
  | 'up-to-date'
  | 'error'
  | 'unsupported'

export interface UpdateStatus {
  phase: UpdatePhase
  currentVersion: string
  version?: string
  releaseNotes?: string
  percent?: number
  message?: string
}

let status: UpdateStatus = {
  phase: 'idle',
  currentVersion: app.getVersion(),
}

let initialized = false

/** NSIS 安装版会写 installed.marker；绿色版 zip 没有，不自动更新 */
function isInstalledBuild(): boolean {
  return app.isPackaged && existsSync(join(dirname(process.execPath), 'installed.marker'))
}

function updateSupported(): boolean {
  return isInstalledBuild() || Boolean(process.env.UPDATE_FEED_URL)
}

function unsupportedMessage(): string {
  if (!app.isPackaged) return '仅安装版支持自动更新'
  return '绿色版请下载新版本手动替换'
}

function broadcast(): void {
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('update:status', status)
  }
}

function setStatus(partial: Partial<UpdateStatus>): void {
  status = { ...status, ...partial, currentVersion: app.getVersion() }
  broadcast()
}

function notesText(info: UpdateInfo): string {
  const notes = info.releaseNotes
  if (typeof notes === 'string') return notes
  if (Array.isArray(notes)) {
    return notes.map((item) => `${item.version}\n${item.note ?? ''}`.trim()).join('\n\n')
  }
  return ''
}

function errorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : ''
  if (message.includes('404')) return '未找到更新发布（404）'
  if (/ENOTFOUND|ETIMEDOUT|ECONNREFUSED|net::/i.test(message)) {
    return '网络不可用，请稍后重试'
  }
  return '检查更新失败，请稍后重试'
}

export async function checkForUpdates(): Promise<UpdateStatus> {
  if (!updateSupported()) {
    setStatus({ phase: 'unsupported', message: unsupportedMessage() })
    return status
  }
  setStatus({ phase: 'checking', message: undefined })
  try {
    await autoUpdater.checkForUpdates()
  } catch (error) {
    log.error('[update] check failed', error)
    setStatus({ phase: 'error', message: errorMessage(error) })
  }
  return status
}

export async function downloadUpdate(): Promise<UpdateStatus> {
  if (status.phase !== 'available') return status
  setStatus({ phase: 'downloading', percent: 0 })
  try {
    await autoUpdater.downloadUpdate()
  } catch (error) {
    log.error('[update] download failed', error)
    setStatus({ phase: 'error', message: errorMessage(error) })
  }
  return status
}

export function installUpdate(): void {
  if (status.phase !== 'downloaded') return
  log.info('[update] quit and install', status.version)
  autoUpdater.quitAndInstall(false, true)
}

export function registerUpdateIpc(): void {
  ipcMain.handle('update:get-state', () => status)
  ipcMain.handle('update:check', () => checkForUpdates())
  ipcMain.handle('update:download', () => downloadUpdate())
  ipcMain.handle('update:install', () => installUpdate())
}

/** 打包态启动后自动检查；失败只记录/渲染端展示，不阻塞启动 */
export function initUpdater(): void {
  if (initialized) return
  initialized = true
  if (!updateSupported()) {
    status.phase = 'unsupported'
    status.message = unsupportedMessage()
    return
  }

  autoUpdater.logger = log
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true
  autoUpdater.allowPrerelease = false
  autoUpdater.allowDowngrade = false

  if (process.env.UPDATE_FEED_URL) {
    autoUpdater.setFeedURL({ provider: 'generic', url: process.env.UPDATE_FEED_URL })
  }

  autoUpdater.on('checking-for-update', () => {
    setStatus({ phase: 'checking', message: undefined })
  })
  autoUpdater.on('update-available', (info) => {
    setStatus({
      phase: 'available',
      version: info.version,
      releaseNotes: notesText(info),
      message: undefined,
    })
  })
  autoUpdater.on('update-not-available', () => {
    setStatus({ phase: 'up-to-date', version: undefined, releaseNotes: undefined })
  })
  autoUpdater.on('download-progress', (progress) => {
    setStatus({ phase: 'downloading', percent: Math.round(progress.percent) })
  })
  autoUpdater.on('update-downloaded', (info) => {
    setStatus({ phase: 'downloaded', version: info.version, percent: 100 })
  })
  autoUpdater.on('error', (error) => {
    log.error('[update] error', error)
    setStatus({ phase: 'error', message: errorMessage(error) })
  })

  setTimeout(() => {
    void checkForUpdates()
  }, 8000)
}
