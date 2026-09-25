/**
 * 音频 overlay 状态。
 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useSelectionStore } from './selection'
import { canGoNext } from '@/utils/canGoNext'
export type AudioPlayerPager = {
  hasMore: () => boolean
  loadingMore: () => boolean
  loadMore: () => Promise<void>
  imageIds: () => number[]
}
export const useAudioPlayerStore = defineStore('audioPlayer', () => {
  const visible = ref(false)
  const playlistIds = ref<number[]>([])
  const currentId = ref<number | null>(null)
  const selection = useSelectionStore()
  let pager: AudioPlayerPager | null = null
  let advancing = false
  const index = computed(() =>
    currentId.value === null ? -1 : playlistIds.value.indexOf(currentId.value))
  const listHasMore = ref(false)
  const listLoadingMore = ref(false)
  const hasPrev = computed(() => index.value > 0)
  const hasNext = computed(() => canGoNext(index.value, playlistIds.value.length, listHasMore.value, listLoadingMore.value))
  function open(id: number, ids: number[]): void {
    playlistIds.value = ids
    currentId.value = id
    visible.value = true
    selection.select(id)
  }

  function close(): void {
    visible.value = false
    currentId.value = null
    playlistIds.value = []
  }
  // 绑定分页器
  function bindPager(next: AudioPlayerPager): void {
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

  function prev(): void {
    if (!hasPrev.value) return
    open(playlistIds.value[index.value - 1], playlistIds.value)
  }

  async function next(): Promise<void> {
    if (advancing) return
    if (index.value < 0) return
    if (index.value < playlistIds.value.length - 1) {
      open(playlistIds.value[index.value + 1], playlistIds.value)
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
        open(playlistIds.value[i + 1], playlistIds.value)
      }
    } finally {
      advancing = false
    }
  }

  return { visible, playlistIds, currentId, open, close, prev, next, hasPrev, hasNext, syncPlaylist, boundImageIds, notifyPager, unbindPager, bindPager }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAudioPlayerStore, import.meta.hot))
}
