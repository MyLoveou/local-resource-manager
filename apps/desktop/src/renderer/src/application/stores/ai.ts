import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  analyzeAIImages,
  clearAIJobs,
  pullVLMModel,
  buildAIIndex,
  getAIJob,
  getAIJobs,
  getAIPerformance,
  getAISuggestions,
  getAIStatus,
  getVLMRuntime,
  installAIModel,
  installAnimeTagger,
  removeAIFeedback,
  searchAI,
  sendAIFeedback,
  selectOllamaBinary,
  selectVLMModel,
  startOllamaRuntime,
  updateAIPerformance,
  type AIJob,
  type AIPerformance,
  type AISearchResult,
  type AIStatus,
  type AISuggestionItem,
  type AIVLMRuntime,
} from '@/infrastructure/http'

export const useAIStore = defineStore('ai', () => {
  const status = ref<AIStatus | null>(null)
  const job = ref<AIJob | null>(null)
  const jobHistory = ref<AIJob[]>([])
  const suggestions = ref<AISuggestionItem[]>([])
  const suggestionsLoading = ref(false)
  const suggestionsLoadingMore = ref(false)
  const suggestionsHasMore = ref(false)
  const results = ref<AISearchResult | null>(null)
  const vlmRuntime = ref<AIVLMRuntime | null>(null)
  const performance = ref<AIPerformance | null>(null)
  const performanceSaving = ref(false)
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

  async function refreshSuggestions(): Promise<void> {
    suggestionsLoading.value = true
    try {
      suggestions.value = await getAISuggestions(60, 0)
      suggestionsHasMore.value = suggestions.value.length >= 60
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载 AI 建议失败'
    } finally {
      suggestionsLoading.value = false
    }
  }

  async function loadMoreSuggestions(): Promise<void> {
    if (suggestionsLoadingMore.value || !suggestionsHasMore.value) return
    suggestionsLoadingMore.value = true
    try {
      const next = await getAISuggestions(60, suggestions.value.length)
      suggestions.value = [...suggestions.value, ...next]
      suggestionsHasMore.value = next.length >= 60
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载 AI 建议失败'
    } finally {
      suggestionsLoadingMore.value = false
    }
  }

  async function refreshVLMRuntime(): Promise<void> {

    try {
      vlmRuntime.value = await getVLMRuntime()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '?? Ollama ????'
    }
  }

  async function refreshPerformance(): Promise<void> {
    try {
      performance.value = await getAIPerformance()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '读取设备信息失败'
    }
  }

  async function savePerformance(payload: {
    mode?: AIPerformance['mode']
    manual?: number
  }): Promise<void> {
    performanceSaving.value = true
    try {
      performance.value = await updateAIPerformance(payload)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '保存 AI 并发设置失败'
    } finally {
      performanceSaving.value = false
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

  async function installAnime(): Promise<void> {
    error.value = ''
    try {
      job.value = await installAnimeTagger()
      await track(job.value.id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '??????????'
    }
  }

  async function buildIndex(full = false): Promise<void> {
    error.value = ''
    results.value = null
    try {
      job.value = await buildAIIndex(full)
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

  async function feedback(
    queryText: string,
    resourceId: number,
    action: 'relevant' | 'irrelevant',
    score?: number,
    position?: number,
  ): Promise<void> {
    try {
      await sendAIFeedback({
        query: queryText,
        resourceId,
        action,
        score,
        position,
      })
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'AI 反馈保存失败'
      throw err
    }
  }

  async function removeFeedback(queryText: string, resourceId: number): Promise<void> {
    try {
      await removeAIFeedback({ query: queryText, resourceId })
    } catch (err) {
      error.value = err instanceof Error ? err.message : '取消 AI 反馈失败'
      throw err
    }
  }

  async function search(query: string, limit = 30, minScore = 0): Promise<void> {
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
      results.value = await searchAI(q, limit, minScore)
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
    suggestions,
    suggestionsLoading,
    suggestionsLoadingMore,
    suggestionsHasMore,
    recentQueries,
    results,
    vlmRuntime,
    performance,
    performanceSaving,
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
    refreshSuggestions,
    loadMoreSuggestions,
    refreshVLMRuntime,
    refreshPerformance,
    savePerformance,
    clearJobHistory,
    installModel,
    installAnime,
    buildIndex,
    feedback,
    removeFeedback,
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
