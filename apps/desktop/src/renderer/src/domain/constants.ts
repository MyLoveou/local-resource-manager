/**
 * 领域常量（与后端 app/shared/constants.py 对齐）
 * 单一事实源：后端 OpenAPI 生成前，手工维护此处 + 后端两份，保持一致
 */

/** 下载协议 */
export const Protocol = {
  HTTP: 'http',
  FTP: 'ftp',
  MAGNET: 'magnet',
  TORRENT: 'torrent',
} as const
export type Protocol = (typeof Protocol)[keyof typeof Protocol]

/** 下载引擎 */
export const DownloadEngine = {
  ARIA2: 'aria2',
  RQBIT: 'rqbit',
  YTDLP: 'yt-dlp',
} as const
export type DownloadEngine = (typeof DownloadEngine)[keyof typeof DownloadEngine]

/** 元数据站点适配器标识 */
export const AdapterKey = {
  OG: 'og',
  TMDB: 'tmdb',
  BANGUMI: 'bangumi',
  PIXIV: 'pixiv',
  DOUBAN: 'douban',
} as const
export type AdapterKey = (typeof AdapterKey)[keyof typeof AdapterKey]

/** 协议 → 默认引擎 路由表（aria2 兼 BT 兜底；rqbit 负责现代 BT/流式） */
export const PROTOCOL_TO_ENGINE: Record<Protocol, DownloadEngine> = {
  [Protocol.HTTP]: DownloadEngine.ARIA2,
  [Protocol.FTP]: DownloadEngine.ARIA2,
  [Protocol.MAGNET]: DownloadEngine.RQBIT,
  [Protocol.TORRENT]: DownloadEngine.RQBIT,
}
