/**
 * 抓取领域类型（与后端 OpenAPI 契约对齐）
 * 后端对应：apps/backend/app/scrape/domain/models.py
 */

import type { WorkCatalog } from './resource'

/** 抓取任务状态机 */
export type ScrapeJobStatus = 'queued' | 'running' | 'done' | 'failed'

/** 元数据抓取任务 */
export interface ScrapeJob {
  id?: number
  resourceId: number
  status: ScrapeJobStatus
  startedAt?: string | null
  finishedAt?: string | null
  error?: string | null
  matchCount: number
  query?: string | null
}

/** 抓取候选（搜索结果条目） */
export interface Candidate {
  id?: number
  jobId: number
  title: string
  url: string
  thumbnailUrl?: string | null
  source: string
  relevance?: number | null
  selected: boolean
  createdAt?: string | null
}

export interface ScrapeCurrent {
  title: string
  synopsis?: string | null
  author?: string | null
  tags: string[]
  catalogSummary?: string | null
}

export interface ScrapePreview {
  title: string
  synopsis?: string | null
  author?: string | null
  tags: string[]
  coverUrls: string[]
  catalog?: WorkCatalog | null
  catalogSummary?: string | null
  sourceRef?: string
  userCoverLocked?: boolean
  current?: ScrapeCurrent
}

export interface ScrapeSelect {
  candidateId: number
  coverUrl?: string | null
  applyTitle?: boolean
  applySynopsis?: boolean
  applyAuthor?: boolean
  applyTags?: boolean
  applyCatalog?: boolean
  applyCover?: boolean
  replaceUserCover?: boolean
}
