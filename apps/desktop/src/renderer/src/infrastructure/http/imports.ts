/**
 * 导入任务（infrastructure/http · /library/imports）
 */
import client from './client'
import type { ResourceType } from '@/domain'

export type ImportSourceKind = 'file' | 'directory'

export interface ImportCreate {
  type: ResourceType
  sourceKind: ImportSourceKind
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
  imported: number
  skippedDuplicate: number
  skippedError: number
  error?: string | null
}

export async function createImport(body: ImportCreate): Promise<ImportJobCreated> {
  const { data } = await client.post<ImportJobCreated>('/library/imports', body)
  return data
}

export async function getImportJob(jobId: string): Promise<ImportJob> {
  const { data } = await client.get<ImportJob>(`/library/imports/${jobId}`)
  return data
}
