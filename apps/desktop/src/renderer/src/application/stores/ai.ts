import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  analyzeAIImages,
  clearAIJobs,
  pullVLMModel,
  buildAIIndex,
  getAIJob,
  getAIJobs,
  getAIStatus,
  getVLMRuntime,
  installAIModel,
  searchAI,
  selectOllamaBinary,
  selectVLMModel,
  startOllamaRuntime,
  type AIJob,
  type AISearchResult,
  type AIStatus,
  type AIVLMRuntime,
} from '@/infrastructure/http'

export const useAIStore = defineStore('ai', () => {
  const status = ref<AIStatus | null>(null)
  const job = ref<AIJob | null>(null)
  const jobHistory = ref<AIJob[]>([])
  const results = ref<AISearchResult | null>(null)
  const vlmRuntime = ref<AIVLMRuntime | null>(null)
  const recentQueries = ref<string[]>(loadRecentQueries())
  const loading = ref(false)
  const searching = ref(false)
  const error = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  const modelInstalled = computed(() => status.value?.model.installed === true)
  const indexed = computed(() => status.value?.indexed ?? 0)
  const total = computed(() => status.value?.total ?? 0)
  const pendingIndex = computed(() => Math.max(0, total.value - indexed.value))
  const canSearch = computed(() => modelInstalled.value && indexed.value > 0)
  const jobActive = computed(() => job.value?.status === 'queued' || job.value?.status === 'running')
  const selectedVLMModel = computed(() => status.value?.captionModel ?? '')
  const vlmModelDetails = computed(() => status.value?.vlmModelDetails ?? [])

  function loadRecentQueries(): string[] {
    try {
      const raw = localStorage.getItem('ai:recent-queries')
      const value = raw ? JSON.parse(raw) : []
      return Array.isArray(value) ? value.filter((item) => typeof item === 'string').slice(0, 12) : []
    } catch {
      return []
    }
  }

  function rememberQuery(query: string): void {
    const value = query.trim()
    if (!value) return
    recentQueries.value = [value, ...recentQueries.value.filter((item) => item !== value)].slice(0, 12)
    try {
      localStorage.setItem('ai:recent-queries', JSON.stringify(recentQueries.value))
    } catch {
      // ignore local storage failures
    }
  }

  function clearRecentQueries(): void {
    recentQueries.value = []
    try {
      localStorage.removeItem('ai:recent-queries')
    } catch {
      // ignore local storage failures
    }
  }

  function stopPolling(): void {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  async function clearJobHistory(): Promise<void> {
    error.value = ''
    try {
      await clearAIJobs()
      jobHistory.value = []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '?? AI ??????'
    }
  }

  async function refreshVLMRuntime(): Promise<void> {
    try {
      vlmRuntime.value = await getVLMRuntime()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '?? Ollama ????'
    }
  }

  async function selectOllama(path: string): Promise<void> {
    error.value = ''
    try {
      vlmRuntime.value = await selectOllamaBinary(path)
      await refresh()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '?? Ollama ????'
    }
  }

  async function startOllama(): Promise<void> {
    error.value = ''
    try {
      vlmRuntime.value = await startOllamaRuntime()
      await refresh()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '?? Ollama ??'
    }
  }

  async function refreshJobs(): Promise<void> {
    try {
      jobHistory.value = await getAIJobs(20)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '?? AI ??????'
    }
  }

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      status.value = await getAIStatus()
      error.value = ''
    } catch (err) {
      error.value = err instanceof Error ? err.message : '读取 AI 状态失败'
    } finally {
      loading.value = false
    }
  }

  async function track(jobId: string): Promise<void> {
    stopPolling()
    try {
      const next = await getAIJob(jobId)
      job.value = next
      if (next.status === 'queued' || next.status === 'running') {
        timer = setTimeout(() => void track(jobId), 800)
        return
      }
      if (next.status === 'error') error.value = next.message || 'AI 任务失败'
      await refresh()
      await refreshJobs()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '读取 AI 任务失败'
      await refresh()
    }
  }

  async function installModel(): Promise<void> {
    error.value = ''
    results.value = null
    try {
      job.value = await installAIModel()
      await track(job.value.id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '安装 AI 模型失败'
    }
  }

  async function buildIndex(): Promise<void> {
    error.value = ''
    results.value = null
    try {
      job.value = await buildAIIndex()
      await track(job.value.id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '建立 AI 索引失败'
    }
  }

  async function pullVLM(model: string): Promise<void> {
    error.value = ''
    try {
      job.value = await pullVLMModel(model)
      await track(job.value.id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '下载 VLM 模型失败'
    }
  }

  async function analyze(resourceIds?: number[], onlyPending = true): Promise<void> {
    error.value = ''
    try {
      job.value = await analyzeAIImages(resourceIds, onlyPending)
      await track(job.value.id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'AI 分析失败'
    }
  }

  async function selectVLM(model: string): Promise<void> {
    error.value = ''
    try {
      status.value = await selectVLMModel(model)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '切换 VLM 模型失败'
    }
  }

  async function search(query: string, limit = 30): Promise<void> {
    const q = query.trim()
    if (!q) {
      results.value = null
      return
    }
    if (jobActive.value) {
      error.value = 'AI 索引正在重建，请稍后再试'
      return
    }
    searching.value = true
    error.value = ''
    try {
      results.value = await searchAI(q, limit)
      rememberQuery(q)
    } catch (err) {
      results.value = null
      error.value = err instanceof Error ? err.message : 'AI 搜索失败'
    } finally {
      searching.value = false
    }
  }

  function clearResults(): void {
    results.value = null
  }

  onScopeDispose(stopPolling)

  return {
    status,
    job,
    jobHistory,
    recentQueries,
    results,
    vlmRuntime,
    loading,
    searching,
    error,
    modelInstalled,
    indexed,
    total,
    pendingIndex,
    canSearch,
    jobActive,
    selectedVLMModel,
    vlmModelDetails,
    refresh,
    refreshJobs,
    refreshVLMRuntime,
    clearJobHistory,
    installModel,
    buildIndex,
    analyze,
    selectVLM,
    selectOllama,
    startOllama,
    pullVLM,
    search,
    clearRecentQueries,
    clearResults,
    stopPolling,
  }
})
