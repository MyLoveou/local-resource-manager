/**
 * 图片查看器：已加载列表内切张；末张可向绑定的分页 loadMore。
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useSelectionStore } from './selection'
import { canGoNext } from '@/utils/canGoNext'

export type ImageViewerPager = {
  hasMore: () => boolean
  loadingMore: () => boolean
  loadMore: () => Promise<void>
  imageIds: () => number[]
}

export const useImageViewerStore = defineStore('imageViewer', () => {
  const visible = ref(false)
  const playlistIds = ref<number[]>([])
  const currentId = ref<number | null>(null)
  const listHasMore = ref(false)
  const listLoadingMore = ref(false)
  const selection = useSelectionStore()
  let pager: ImageViewerPager | null = null
  let advancing = false

  const index = computed(() =>
    currentId.value === null ? -1 : playlistIds.value.indexOf(currentId.value)
  )
  const hasPrev = computed(() => index.value > 0)
  const hasNext = computed(() =>
    canGoNext(index.value, playlistIds.value.length, listHasMore.value, listLoadingMore.value)
  )
  // 绑定分页器
  function bindPager(next: ImageViewerPager): void {
    pager = next
    listHasMore.value = next.hasMore()
    listLoadingMore.value = next.loadingMore()
  }
  // 解除绑定分页器
  function unbindPager(): void {
    pager = null
    listHasMore.value = false
    listLoadingMore.value = false
  }
  // 通知分页器更新
  function notifyPager(): void {
    listHasMore.value = pager?.hasMore() ?? false
    listLoadingMore.value = pager?.loadingMore() ?? false
  }
  // 获取绑定分页器的图片 ID 列表
  function boundImageIds(): number[] {
    return pager?.imageIds() ?? []
  }
  // 同步播放列表
  function syncPlaylist(ids: number[]): void {
    if (!visible.value) return
    playlistIds.value = ids
  }
  // 打开查看器
  function open(id: number, ids: number[]): void {
    playlistIds.value = ids
    currentId.value = id
    visible.value = true
    selection.select(id)
  }
  // 关闭查看器
  function close(): void {
    visible.value = false
    currentId.value = null
    playlistIds.value = []
  }

  function show(id: number): void {
    currentId.value = id
    selection.select(id)
  }

  function prev(): void {
    if (!hasPrev.value) return
    show(playlistIds.value[index.value - 1])
  }

  async function next(): Promise<void> {
    if (advancing) return
    if (index.value < 0) return
    if (index.value < playlistIds.value.length - 1) {
      show(playlistIds.value[index.value + 1])
      return
    }
    if (!pager) return
    if (!pager.hasMore() && !pager.loadingMore()) return
    const waitedId = currentId.value
    advancing = true
    try {
      await pager.loadMore()
      if (!visible.value || !pager) return
      if (currentId.value !== waitedId) return
      playlistIds.value = pager.imageIds()
      const i = waitedId === null ? -1 : playlistIds.value.indexOf(waitedId)
      if (i >= 0 && i < playlistIds.value.length - 1) {
        show(playlistIds.value[i + 1])
      }
    } finally {
      advancing = false
    }
  }

  return {
    visible,
    playlistIds,
    currentId,
    hasPrev,
    hasNext,
    bindPager,
    unbindPager,
    notifyPager,
    boundImageIds,
    syncPlaylist,
    open,
    close,
    prev,
    next,
  }
})
