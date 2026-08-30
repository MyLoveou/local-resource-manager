/**
 * 抓取领域类型（与后端 OpenAPI 契约对齐）
 * 后端对应：apps/backend/app/scrape/domain/models.py
 */

/** 抓取任务状态机 */
export type ScrapeJobStatus = 'queued' | 'running' | 'done' | 'failed'

/** 元数据抓取任务 */
export interface ScrapeJob {
  id?: number
  resourceId: number
  status: ScrapeJobStatus
  startedAt?: string | null
  finishedAt?: string | null
  /** 失败原因 */
  error?: string | null
  /** 命中候选数 */
  matchCount: number
}

/** 抓取候选（搜索结果条目） */
export interface Candidate {
  id?: number
  jobId: number
  title: string
  url: string
  thumbnailUrl?: string | null
  /** 来源适配器/站点标识（SearXNG / TMDB / Bangumi / 反查图…） */
  source: string
  /** 相关度 0-1 */
  relevance?: number | null
  /** 用户是否选中回填 */
  selected: boolean
  createdAt?: string | null
}
