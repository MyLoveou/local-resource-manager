/**
 * 视频播放器覆盖层状态。
 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'
import { useSelectionStore } from './selection'

export const useVideoPlayerStore = defineStore('videoPlayer', () => {
  const visible = ref(false)
  const playlistIds = ref<number[]>([])
  const currentId = ref<number | null>(null)
  const currentFileId = ref<number | null>(null)
  const selection = useSelectionStore()

  function open(id: number, ids: number[], fileId?: number | null): void {
    playlistIds.value = ids
    currentId.value = id
    currentFileId.value = fileId ?? null
    visible.value = true
    selection.select(id)
  }

  function close(): void {
    visible.value = false
    currentId.value = null
    currentFileId.value = null
    playlistIds.value = []
  }

  function show(id: number): void {
    currentId.value = id
    selection.select(id)
  }


  return { visible, playlistIds, currentId, currentFileId, open, close }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useVideoPlayerStore, import.meta.hot))
}
