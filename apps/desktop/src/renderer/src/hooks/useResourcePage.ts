/**
 * 资源分页状态机：首屏替换、触底 keyset 追加、bump 只重拉首页。
 */
import { computed, onMounted, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { getResources, invalidateResourceCache } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { Resource, ResourceStatus, ResourceType } from '@/domain'

const DEFAULT_LIMIT = 80

export function useResourcePage(options: {
  type?: MaybeRefOrGetter<ResourceType | undefined>
  status?: MaybeRefOrGetter<ResourceStatus | undefined>
  q?: MaybeRefOrGetter<string>
  sort?: MaybeRefOrGetter<string>
  order?: MaybeRefOrGetter<'asc' | 'desc'>
  tagIds?: MaybeRefOrGetter<number[]>
  limit?: number
}) {
  const items = ref<Resource[]>([])
  const total = ref(0)
  const hasMore = ref(true)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref<unknown>(null)

  let requestId = 0
  let inflight: Promise<void> | null = null
  let inflightAppend = false
  let cursorKey: string | undefined
  let cursorId: number | undefined
  const limit = options.limit ?? DEFAULT_LIMIT
  const type = computed(() => toValue(options.type))
  const status = computed(() => toValue(options.status) ?? 'active')
  const q = computed(() => toValue(options.q) ?? '')
  const sort = computed(() => toValue(options.sort) ?? 'createdAt')
  const order = computed(() => toValue(options.order) ?? 'desc')
  const tagIds = computed(() => toValue(options.tagIds) ?? [])

  async function fetchPage(append: boolean): Promise<void> {
    const run = runFetch(append)
    inflight = run
    inflightAppend = append
    try {
      await run
    } finally {
      if (inflight === run) {
        inflight = null
        inflightAppend = false
      }
    }
  }

  async function runFetch(append: boolean): Promise<void> {
    const id = ++requestId
    loading.value = true
    loadingMore.value = append
    error.value = null
    try {
      const page = await getResources({
        type: type.value,
        status: status.value,
        limit,
        sort: sort.value,
        order: order.value,
        q: q.value.trim() || undefined,
        tagIds: tagIds.value.length ? tagIds.value : undefined,
        afterKey: append ? cursorKey : undefined,
        afterId: append ? cursorId : undefined,
      })
      if (id !== requestId) return
      total.value = page.total
      hasMore.value = page.hasMore
      if (append) {
        const seen = new Set(items.value.map((item) => item.id))
        items.value = [
          ...items.value,
          ...page.items.filter((item) => item.id !== undefined && !seen.has(item.id)),
        ]
      } else {
        items.value = page.items
      }
      const last = items.value[items.value.length - 1]
      cursorKey = page.nextKey ?? undefined
      cursorId = page.nextId ?? last?.id
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
    cursorKey = undefined
    cursorId = undefined
    await fetchPage(false)
  }

  async function loadMore(): Promise<void> {
    const waitingAppend = inflight != null && inflightAppend
    if (inflight) await inflight
    if (waitingAppend) return
    if (!hasMore.value || loading.value) return
    await fetchPage(true)
  }

  onMounted(() => {
    void reset()
  })

  const library = useLibraryStore()
  watch(
    () => library.revision,
    () => {
      invalidateResourceCache()
      if (
        type.value === undefined ||
        library.importedType === null ||
        library.importedType === type.value
      ) {
        void reset()
      }
    }
  )

  watch([type, q, sort, order, tagIds], () => {
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
