/**
 * 渲染进程日志薄封装。
 * 经 preload → 主进程落盘；文件格式由主进程 unifiedFormat 统一。
 * DevTools 控制台使用同一模板，便于对照。
 */
import log from 'electron-log/renderer'

log.variables.processType = 'renderer'
log.transports.console.format = '{y}-{m}-{d} {h}:{i}:{s} - [renderer] - {level} - {text}'

export const logger = {
  debug: (...args: unknown[]) => log.debug(...args),
  info: (...args: unknown[]) => log.info(...args),
  warn: (...args: unknown[]) => log.warn(...args),
  error: (...args: unknown[]) => log.error(...args),
}

export default logger
