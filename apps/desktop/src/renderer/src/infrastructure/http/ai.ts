import type { Resource } from '@/domain'
import client from './client'

export interface AIModelInfo {
  id: string
  name: string
  installed: boolean
  dim: number
  sizeBytes: number
}

export interface AIStatus {
  dependencyReady: boolean
  model: AIModelInfo
  indexed: number
  total: number
  personCountIndexed: number
  indexUpdatedAt: string | null
}

export interface AIJob {
  id: string
  kind: 'install' | 'index' | string
  status: 'queued' | 'running' | 'done' | 'error' | string
  total: number
  done: number
  percent: number | null
  message: string
  createdAt: string
  updatedAt: string
}

export interface AISearchResult {
  items: Resource[]
  scores: number[]
  indexed: number
  matched: number
  returned: number
  filters: string[]
}

export async function getAIStatus(): Promise<AIStatus> {
  const { data } = await client.get<AIStatus>('/ai/status')
  return data
}

export async function installAIModel(): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/models/install')
  return data
}

export async function buildAIIndex(): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/index')
  return data
}

export async function getAIJob(jobId: string): Promise<AIJob> {
  const { data } = await client.get<AIJob>(`/ai/jobs/${jobId}`)
  return data
}

export async function searchAI(q: string, limit = 30): Promise<AISearchResult> {
  const { data } = await client.get<AISearchResult>('/ai/search', {
    params: { q, limit },
    timeout: 30000,
  })
  return data
}


export interface AISimilarResult {
  mode: string
  indexed: number
  returned: number
  items: Resource[]
  scores: number[]
  duplicates: Resource[]
  duplicateScores: number[]
}

export async function getAISimilar(
  resourceId: number,
  mode = 'auto',
  limit = 30,
): Promise<AISimilarResult> {
  const { data } = await client.get<AISimilarResult>('/ai/similar', {
    params: { resourceId, mode, limit },
    timeout: 30000,
  })
  return data
}
