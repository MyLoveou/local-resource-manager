/**
 * 资源分页状态机：首屏替换、触底追加、请求单飞。
 */
import { onMounted, ref } from 'vue'
import { getResources } from '@/infrastructure/http'
import type { Resource, ResourceStatus, ResourceType } from '@/domain'

const DEFAULT_LIMIT = 80

export function useResourcePage(options: {
  type: ResourceType
  status?: ResourceStatus
  limit?: number
}) {
  const items = ref<Resource[]>([])
  const total = ref(0)
  const hasMore = ref(true)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref<unknown>(null)

  let requestId = 0
  const limit = options.limit ?? DEFAULT_LIMIT
  const status = options.status ?? 'active'

  async function fetchPage(offset: number, append: boolean): Promise<void> {
    const id = ++requestId
    loading.value = true
    loadingMore.value = append
    error.value = null
    try {
      const page = await getResources({
        type: options.type,
        status,
        limit,
        offset,
        sort: 'createdAt',
        order: 'desc',
      })
      // 如果请求ID不匹配，说明请求已经完成，直接返回
      if (id !== requestId) return
      total.value = page.total
      hasMore.value = page.hasMore
      // 如果追加请求，则将新数据添加到已有数据中
      if (append) {
        const seen = new Set(items.value.map((item) => item.id))
        items.value = [
          ...items.value,
          ...page.items.filter((item) => item.id !== undefined && !seen.has(item.id)),
        ]
      } else {
        items.value = page.items
      }
    } catch (err) {
      if (id !== requestId) return
      error.value = err
      if (!append) {
        items.value = []
        total.value = 0
        hasMore.value = false
      }
    } finally {
      if (id === requestId) {
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  async function reset(): Promise<void> {
    hasMore.value = true
    await fetchPage(0, false)
  }

  async function loadMore(): Promise<void> {
    if (!hasMore.value || loading.value) return
    await fetchPage(items.value.length, true)
  }

  onMounted(() => {
    void reset()
  })

  return {
    items,
    total,
    hasMore,
    loading,
    loadingMore,
    error,
    reset,
    loadMore,
  }
}
