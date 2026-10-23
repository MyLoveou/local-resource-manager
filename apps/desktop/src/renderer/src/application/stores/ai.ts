import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  analyzeAIImages,
  pullVLMModel,
  buildAIIndex,
  getAIJob,
  getAIStatus,
  installAIModel,
  searchAI,
  type AIJob,
  type AISearchResult,
  type AIStatus,
} from '@/infrastructure/http'

export const useAIStore = defineStore('ai', () => {
  const status = ref<AIStatus | null>(null)
  const job = ref<AIJob | null>(null)
  const results = ref<AISearchResult | null>(null)
  const loading = ref(false)
  const searching = ref(false)
  const error = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  const modelInstalled = computed(() => status.value?.model.installed === true)
  const indexed = computed(() => status.value?.indexed ?? 0)
  const total = computed(() => status.value?.total ?? 0)
  const canSearch = computed(() => modelInstalled.value && indexed.value > 0)
  const jobActive = computed(() => job.value?.status === 'queued' || job.value?.status === 'running')

  function stopPolling(): void {
    if (timer) {
      clearTimeout(timer)
      timer = null
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

  async function analyze(resourceIds?: number[]): Promise<void> {
    error.value = ''
    try {
      job.value = await analyzeAIImages(resourceIds)
      await track(job.value.id)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'AI 分析失败'
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
    results,
    loading,
    searching,
    error,
    modelInstalled,
    indexed,
    total,
    canSearch,
    jobActive,
    refresh,
    installModel,
    buildIndex,
    analyze,
    pullVLM,
    search,
    clearResults,
    stopPolling,
  }
})
