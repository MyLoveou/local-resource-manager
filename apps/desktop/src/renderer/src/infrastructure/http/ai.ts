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
  captionReady: boolean
  captionModel: string
  captionIndexed: number
  vlmRuntimeReady: boolean
  vlmModels: string[]
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

export interface AIQueryInsight {
  source: 'text' | 'image' | string
  raw: string
  semanticText: string
  strategy: string
  caption: string
  shortCaption: string
  tags: string[]
  labels: string[]
  filters: string[]
  personCount: number | null
  orientation: string | null
  notes: string[]
}

export interface AIMatchExplanation {
  resourceId: number
  reasons: string[]
  semanticScore: number | null
  duplicateScore: number | null
  dhashDistance: number | null
  caption: string
  shortCaption: string
  tags: string[]
  matchedLabels: string[]
  personCount: number | null
  orientation: string | null
}

export interface AISearchResult {
  items: Resource[]
  scores: number[]
  indexed: number
  matched: number
  returned: number
  filters: string[]
  queryInsight: AIQueryInsight | null
  explanations: AIMatchExplanation[]
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
  queryInsight: AIQueryInsight | null
  explanations: AIMatchExplanation[]
  duplicateExplanations: AIMatchExplanation[]
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


export interface AIFusionResult {
  mode: string
  indexed: number
  matched: number
  returned: number
  items: Resource[]
  scores: number[]
  filters: string[]
}

export interface AIFusionOptions {
  strict?: boolean
  imageWeight?: number
  textWeight?: number
  limit?: number
}

export async function searchAIFusion(
  resourceId: number,
  query: string,
  options: AIFusionOptions = {},
): Promise<AIFusionResult> {
  const { data } = await client.post<AIFusionResult>(
    '/ai/search/fusion',
    {
      resourceId,
      query,
      limit: options.limit ?? 30,
      strict: options.strict ?? false,
      imageWeight: options.imageWeight ?? 0.5,
      textWeight: options.textWeight ?? 0.5,
    },
    { timeout: 30000 },
  )
  return data
}


export async function searchAISimilarFile(
  file: File,
  mode = 'auto',
  limit = 30,
): Promise<AISimilarResult> {
  const dataBase64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result ?? '')
      resolve(result.includes(',') ? result.slice(result.indexOf(',') + 1) : result)
    }
    reader.onerror = () => reject(reader.error ?? new Error('读取图片失败'))
    reader.readAsDataURL(file)
  })
  const { data } = await client.post<AISimilarResult>(
    '/ai/similar/file',
    { filename: file.name, dataBase64, mode, limit },
    { timeout: 30000 },
  )
  return data
}


export async function analyzeAIImages(resourceIds?: number[]): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/analyze', {
    resourceIds: resourceIds ?? null,
  })
  return data
}


export async function pullVLMModel(model: string): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/vlm/pull', { model })
  return data
}
