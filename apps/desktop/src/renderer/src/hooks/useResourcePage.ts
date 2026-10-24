/**
 * 资源分页状态机：首屏替换、触底 keyset 追加、resourceRevision 变化重拉第一页。
 */
import { computed, onMounted, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { getResources, invalidateResourceCache } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { CollectionCardData, Resource, ResourceStatus, ResourceType } from '@/domain'

const DEFAULT_LIMIT = 80

export function useResourcePage(options: {
  type?: MaybeRefOrGetter<ResourceType | undefined>
  status?: MaybeRefOrGetter<ResourceStatus | undefined>
  q?: MaybeRefOrGetter<string>
  sort?: MaybeRefOrGetter<string>
  order?: MaybeRefOrGetter<'asc' | 'desc'>
  tagIds?: MaybeRefOrGetter<number[]>
  characterIds?: MaybeRefOrGetter<number[]>
  personIds?: MaybeRefOrGetter<number[]>
  categoryIds?: MaybeRefOrGetter<number[]>
  uncategorized?: MaybeRefOrGetter<boolean>
  includeCollected?: MaybeRefOrGetter<boolean>
  takenDate?: MaybeRefOrGetter<string | undefined>
  untimed?: MaybeRefOrGetter<boolean>
  timelineVisible?: MaybeRefOrGetter<boolean | undefined>
  timelineMedia?: MaybeRefOrGetter<boolean>
  limit?: number
}) {
  const items = ref<(Resource | CollectionCardData)[]>([])
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
  const characterIds = computed(() => toValue(options.characterIds) ?? [])
  const personIds = computed(() => toValue(options.personIds) ?? [])
  const categoryIds = computed(() => toValue(options.categoryIds) ?? [])
  const uncategorized = computed(() => toValue(options.uncategorized) ?? false)
  const includeCollected = computed(() => toValue(options.includeCollected) ?? false)
  const takenDate = computed(() => toValue(options.takenDate))
  const untimed = computed(() => toValue(options.untimed) ?? false)
  const timelineVisible = computed(() => toValue(options.timelineVisible))
  const timelineMedia = computed(() => toValue(options.timelineMedia) ?? false)

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
        characterIds: characterIds.value.length ? characterIds.value : undefined,
        personIds: personIds.value.length ? personIds.value : undefined,
        categoryIds: categoryIds.value.length ? categoryIds.value : undefined,
        uncategorized: uncategorized.value,
        includeCollected: includeCollected.value,
        takenDate: takenDate.value,
        untimed: untimed.value,
        timelineVisible: timelineVisible.value,
        timelineMedia: timelineMedia.value,
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

  /** 监视导入软刷新：重拉首页，只把新项插到列表头部，保留浏览位置。 */
  async function refreshTop(): Promise<void> {
    const id = ++requestId
    loading.value = true
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
        characterIds: characterIds.value.length ? characterIds.value : undefined,
        personIds: personIds.value.length ? personIds.value : undefined,
        categoryIds: categoryIds.value.length ? categoryIds.value : undefined,
        uncategorized: uncategorized.value,
        includeCollected: includeCollected.value,
        takenDate: takenDate.value,
        untimed: untimed.value,
        timelineVisible: timelineVisible.value,
        timelineMedia: timelineMedia.value,
      })
      if (id !== requestId) return
      total.value = page.total
      hasMore.value = page.hasMore
      const seen = new Set(items.value.map((item) => item.id))
      const fresh = page.items.filter((item) => item.id !== undefined && !seen.has(item.id))
      if (fresh.length) {
        items.value = [...fresh, ...items.value]
      }
    } catch (err) {
      if (id !== requestId) return
      error.value = err
    } finally {
      if (id === requestId) {
        loading.value = false
        loadingMore.value = false
      }
    }
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
    () => library.resourceRevision(type.value),
    () => {
      invalidateResourceCache()
      void reset()
    }
  )

  watch(
    () => library.watchRevision,
    () => {
      invalidateResourceCache()
      if (
        type.value === undefined ||
        library.watchType === null ||
        library.watchType === type.value
      ) {
        void refreshTop()
      }
    }
  )

  watch([type, q, sort, order, tagIds, characterIds, personIds, categoryIds, uncategorized, includeCollected, takenDate, untimed, timelineVisible, timelineMedia], () => {
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
    refreshTop,
    loadMore,
  }
}
