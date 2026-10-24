import type { Resource } from '@/domain'
import client from './client'

export interface AIModelInfo {
  id: string
  name: string
  installed: boolean
  dim: number
  sizeBytes: number
}

export interface AIVLMRuntime {
  running: boolean
  url: string
  binaryPath: string
  detected: boolean
  modelsDir: string
  error: string
}

export interface AIVLMModelInfo {
  name: string
  sizeBytes: number
  capabilities: string[]
  supportsVision: boolean
  selected: boolean
}

export interface AIDeviceInfo {
  cpuCount: number
  memoryTotalBytes: number
  memoryAvailableBytes: number
  gpuName: string
  vramTotalBytes: number
  vramFreeBytes: number
  platform: string
}

export interface AIPerformance {
  device: AIDeviceInfo
  mode: 'safe' | 'balanced' | 'max' | 'manual'
  manual: number
  effective: number
  safe: number
  balanced: number
  max: number
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
  vlmProvider: string
  animeTaggerReady: boolean
  animeTaggerSize: number
  vlmModels: string[]
  vlmModelDetails: AIVLMModelInfo[]
  indexUpdatedAt: string | null
}

export interface AIJob {
  id: string
  kind: 'install' | 'index' | string
  status: 'queued' | 'running' | 'done' | 'error' | string
  total: number
  done: number
  failed: number
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

export interface AIEntitySuggestion {
  id: number
  name: string
}

export interface AISuggestionItem {
  resourceId: number
  title: string
  thumbnailPath: string | null
  tags: string[]
  characters: AIEntitySuggestion[]
  persons: AIEntitySuggestion[]
  collections: AIEntitySuggestion[]
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
  minScore: number
  filteredLowScore: number
  captionMatched: number
  feedbackAdjusted: number
  feedback: Record<string, 'relevant' | 'irrelevant'>
  explored: boolean
}

export async function getAIStatus(): Promise<AIStatus> {
  const { data } = await client.get<AIStatus>('/ai/status')
  return data
}

export async function getAIPerformance(): Promise<AIPerformance> {
  const { data } = await client.get<AIPerformance>('/ai/performance')
  return data
}

export async function updateAIPerformance(payload: {
  mode?: AIPerformance['mode']
  manual?: number
}): Promise<AIPerformance> {
  const { data } = await client.patch<AIPerformance>('/ai/performance', payload)
  return data
}

export async function installAnimeTagger(): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/anime/install')
  return data
}

export async function installAIModel(): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/models/install')
  return data
}

export async function buildAIIndex(full = false): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/index', { full })
  return data
}

export async function getAIJob(jobId: string): Promise<AIJob> {
  const { data } = await client.get<AIJob>(`/ai/jobs/${jobId}`)
  return data
}

export async function searchAI(
  q: string,
  limit = 30,
  minScore = 0,
): Promise<AISearchResult> {
  const { data } = await client.get<AISearchResult>('/ai/search', {
    params: { q, limit, minScore },
    timeout: 30000,
  })
  return data
}

export async function sendAIFeedback(payload: {
  query: string
  resourceId: number
  action: 'relevant' | 'irrelevant'
  source?: string
  score?: number
  position?: number
}): Promise<void> {
  await client.post('/ai/feedback', payload)
}

export async function removeAIFeedback(payload: {
  query: string
  resourceId: number
  source?: string
}): Promise<void> {
  await client.delete('/ai/feedback', { params: payload })
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


export async function analyzeAIImages(
  resourceIds?: number[],
  onlyPending = true,
): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/analyze', {
    resourceIds: resourceIds ?? null,
    onlyPending,
  })
  return data
}

export async function getAISuggestions(limit = 30, offset = 0): Promise<AISuggestionItem[]> {
  const { data } = await client.get<AISuggestionItem[]>('/ai/suggestions', {
    params: { limit, offset },
  })
  return data
}

export async function getVLMRuntime(): Promise<AIVLMRuntime> {
  const { data } = await client.get<AIVLMRuntime>('/ai/vlm/runtime')
  return data
}

export async function selectOllamaBinary(path: string): Promise<AIVLMRuntime> {
  const { data } = await client.post<AIVLMRuntime>('/ai/vlm/runtime/select', { path })
  return data
}

export async function startOllamaRuntime(): Promise<AIVLMRuntime> {
  const { data } = await client.post<AIVLMRuntime>('/ai/vlm/runtime/start')
  return data
}

export async function getAIJobs(limit = 20): Promise<AIJob[]> {
  const { data } = await client.get<AIJob[]>('/ai/jobs', { params: { limit } })
  return data
}

export async function clearAIJobs(): Promise<void> {
  await client.delete('/ai/jobs')
}

export async function selectVLMModel(model: string): Promise<AIStatus> {
  const { data } = await client.post<AIStatus>('/ai/vlm/select', { model })
  return data
}


export async function pullVLMModel(model: string): Promise<AIJob> {
  const { data } = await client.post<AIJob>('/ai/vlm/pull', { model })
  return data
}
