/**
 * 首页概览类型（后端 /library/overview，camelCase 契约）
 * 后端对应：apps/backend/app/library/application/schemas.py
 */
import type { Resource } from './resource'
import type { ResourceType } from './resource'
/** 资源统计 */
export interface ResourceStats {
  byType: Record<ResourceType, number>
  totalSizeBytes: number
  trashedCount: number
  lostCount: number
}

/** 进行中任务概览 */
export interface TaskSummary {
  runningScrapeJobs: number
  failedScrapeJobs: number
  activeDownloads: number
}

/** 首页概览：统计 + 最近添加 + 任务 */
export interface Overview {
  stats: ResourceStats
  recent: Resource[]
  tasks: TaskSummary
}
