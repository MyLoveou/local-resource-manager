/**
 * 主进程日志：electron-log 落盘 + 控制台。
 * 必须在 createWindow 之前调用 initMainLog()。
 *
 * 与后端统一格式：
 *   YYYY-MM-DD HH:mm:ss - [scope] - LEVEL - message
 * scope: main | renderer | backend
 *
 * 与后端统一目录（getLogDir）：
 *   - LOG_DIR 环境变量优先
 *   - 开发：{repo}/apps/logs
 *   - 生产：{userData}/logs
 */
import { app } from 'electron'
import { mkdirSync } from 'fs'
import { join, resolve } from 'path'
import log from 'electron-log/main'
import dayjs from 'dayjs'

/** 前后端共用的日志目录 */
export function getLogDir(): string {
  if (process.env.LOG_DIR) return process.env.LOG_DIR
  // electron-vite dev 会设 ELECTRON_RENDERER_URL
  if (process.env.ELECTRON_RENDERER_URL) {
    const root = process.env.PROJECT_ROOT ?? resolve(app.getAppPath(), '../..')
    return join(root, 'apps/logs')
  }
  return join(app.getPath('userData'), 'logs')
}

/** 与 apps/backend LoggingConfig 对齐 */
function unifiedFormat({ message }: { message: {
  date: Date
  level: string
  data: unknown[]
  variables?: { processType?: string }
} }): unknown[] {
  const ts = dayjs(message.date).format('YYYY-MM-DD HH:mm:ss')
  const raw = message.variables?.processType ?? 'main'
  const scope = raw === 'browser' ? 'main' : raw
  const level = String(message.level).toUpperCase()
  return [`${ts} - [${scope}] - ${level} -`, ...message.data]
}

export function initMainLog(): void {
  const logDir = getLogDir()
  mkdirSync(logDir, { recursive: true })
  // 供后端子进程继承；显式再传一遍更稳
  process.env.LOG_DIR = logDir

  log.initialize()
  log.variables.processType = 'main'

  const isDev = Boolean(process.env.ELECTRON_RENDERER_URL)
  log.transports.file.level = 'info'
  log.transports.console.level = isDev ? 'debug' : 'info'
  log.transports.file.maxSize = 10 * 1024 * 1024
  log.transports.file.resolvePathFn = () => join(logDir, 'main.log')
  log.transports.file.format = unifiedFormat
  log.transports.console.format = unifiedFormat
  log.errorHandler.startCatching()

  log.info('[main] log dir', logDir)
}

export { log }
export default log
