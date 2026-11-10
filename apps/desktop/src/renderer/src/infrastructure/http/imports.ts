/**
 * 导入任务（infrastructure/http · /library/imports）
 */
import client from './client'
import type { ResourceType, StorageKind } from '@/domain'
import { SourceKind } from '@/domain'

export type ImportSourceKind = SourceKind

export interface ImportCreate {
  type: ResourceType
  sourceKind: ImportSourceKind
  storageKind?: StorageKind
  timelineVisible?: boolean
  mapVisible?: boolean
  categoryIds?: number[]
  tagNames?: string[]
  paths: string[]
}

export interface ImportJobCreated {
  jobId: string
}

export interface ImportJob {
  jobId: string
  status: string
  phase: string
  total: number
  done: number
  percent?: number
  etaSeconds?: number | null
  speedMbps?: number | null
  imported: number
  skippedDuplicate: number
  skippedError: number
  error?: string | null
  message?: string | null
  code?: string | null
  details?: string[]
}

export async function createImport(body: ImportCreate): Promise<ImportJobCreated> {
  const { data } = await client.post<ImportJobCreated>('/library/imports', body)
  return data
}

export async function getImportJob(jobId: string): Promise<ImportJob> {
  const { data } = await client.get<ImportJob>(`/library/imports/${jobId}`)
  return data
}

export interface PreviewEpisode {
  season: number
  episode: number
  title?: string | null
  file: string
}

export interface PreviewSeason {
  season: number
  episodes: PreviewEpisode[]
}

export interface PreviewExtra {
  title: string
  file: string
}

export interface ImportPreview {
  ok: boolean
  code?: string | null
  message: string
  details: string[]
  totalFiles: number
  seasons: PreviewSeason[]
  extras: PreviewExtra[]
}

export async function previewImport(body: {
  type: ResourceType
  path: string
}): Promise<ImportPreview> {
  const { data } = await client.post<ImportPreview>('/library/imports/preview', body)
  return data
}