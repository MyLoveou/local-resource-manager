/**
 * 下载领域类型（与后端 OpenAPI 契约对齐）
 * 后端对应：apps/backend/app/download/domain/models.py
 */
import type { DownloadEngine, Protocol } from './constants'

/** 下载任务状态机 */
export type DownloadStatus = 'queued' | 'running' | 'paused' | 'done' | 'failed'

/** 下载任务（状态权威存于后端） */
export interface DownloadTask {
  id?: number
  url: string
  protocol: Protocol
  engine: DownloadEngine
  status: DownloadStatus
  savePath?: string | null
  downloadedBytes: number
  totalBytes?: number | null
  /** 字节/秒 */
  speed: number
  /** 失败原因 */
  error?: string | null
  /** 完成入库后关联的资源 */
  targetResourceId?: number | null
  createdAt?: string | null
  updatedAt?: string | null
}
