/**
 * 领域常量（与后端对齐）
 * 单一事实源：后端 OpenAPI 生成前，手工维护此处 + 后端两份，保持一致
 * 下载域常量（Protocol / DownloadEngine / PROTOCOL_TO_ENGINE）已随下载功能移除（D-20261007-01）
 */

/** 元数据站点适配器标识 */
export const AdapterKey = {
  OG: 'og',
  TMDB: 'tmdb',
  BANGUMI: 'bangumi',
  PIXIV: 'pixiv',
  DOUBAN: 'douban',
} as const
export type AdapterKey = (typeof AdapterKey)[keyof typeof AdapterKey]

/** 导入来源（与后端 SourceKind 对齐） */
export const SourceKind = {
  FILE: 'file',
  DIRECTORY: 'directory',
} as const
export type SourceKind = (typeof SourceKind)[keyof typeof SourceKind]

/** 点开头的文件/目录不参与导入收集 */
export const HIDDEN_NAME_PREFIX = '.'

export const API_CODE_OK = 0
export const API_STATUS_SUCCESS = 'success'
export const API_STATUS_ERROR = 'error'

/** 网格列宽随窗口变化的节流间隔 */
export const GRID_RESIZE_THROTTLE_MS = 150
