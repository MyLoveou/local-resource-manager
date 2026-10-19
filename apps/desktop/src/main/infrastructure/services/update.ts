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
  transferred?: number
  total?: number
  bytesPerSecond?: number
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

function decodeEntities(value: string): string {
  const named: Record<string, string> = {
    amp: '&',
    apos: "'",
    gt: '>',
    hellip: '…',
    lt: '<',
    mdash: '—',
    nbsp: ' ',
    ndash: '–',
    quot: '"',
  }
  return value.replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (match, entity: string) => {
    const key = entity.toLowerCase()
    if (key.startsWith('#x')) {
      const code = Number.parseInt(key.slice(2), 16)
      return Number.isNaN(code) ? match : String.fromCodePoint(code)
    }
    if (key.startsWith('#')) {
      const code = Number.parseInt(key.slice(1), 10)
      return Number.isNaN(code) ? match : String.fromCodePoint(code)
    }
    return named[key] ?? match
  })
}

/** GitHub Atom feed 的更新说明是 HTML；渲染端只展示纯文本，避免把 <p> 原样显示 */
function htmlToText(value: string): string {
  return decodeEntities(
    value
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(?:p|div|h[1-6]|li|tr)>/gi, '\n')
      .replace(/<li[^>]*>/gi, '• ')
      .replace(/<[^>]*>/g, '')
  )
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function notesText(info: UpdateInfo): string {
  const notes = info.releaseNotes
  if (typeof notes === 'string') return htmlToText(notes)
  if (Array.isArray(notes)) {
    return notes
      .map((item) => {
        const note = htmlToText(item.note ?? '')
        return `${item.version}${note ? `\n${note}` : ''}`
      })
      .join('\n\n')
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
  setStatus({ phase: 'downloading', percent: 0, transferred: 0, bytesPerSecond: 0 })
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
    setStatus({
      phase: 'checking',
      message: undefined,
      percent: undefined,
      transferred: undefined,
      total: undefined,
      bytesPerSecond: undefined,
    })
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
    setStatus({
      phase: 'up-to-date',
      version: undefined,
      releaseNotes: undefined,
      percent: undefined,
      transferred: undefined,
      total: undefined,
      bytesPerSecond: undefined,
    })
  })
  autoUpdater.on('download-progress', (progress) => {
    setStatus({
      phase: 'downloading',
      percent: Math.round(progress.percent),
      transferred: progress.transferred,
      total: progress.total,
      bytesPerSecond: Math.round(progress.bytesPerSecond),
    })
  })
  autoUpdater.on('update-downloaded', (info) => {
    setStatus({
      phase: 'downloaded',
      version: info.version,
      percent: 100,
      bytesPerSecond: undefined,
    })
  })
  autoUpdater.on('error', (error) => {
    log.error('[update] error', error)
    setStatus({ phase: 'error', message: errorMessage(error) })
  })

  setTimeout(() => {
    void checkForUpdates()
  }, 8000)
}
