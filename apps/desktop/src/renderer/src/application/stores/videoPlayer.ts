/**
 * 视频播放器覆盖层状态。
 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'
import { useSelectionStore } from './selection'
import logger from '@/infrastructure/logging/logger'

export const useVideoPlayerStore = defineStore('videoPlayer', () => {
  const visible = ref(false)
  const playlistIds = ref<number[]>([])
  const currentId = ref<number | null>(null)
  const selection = useSelectionStore()

  function open(id: number, ids: number[]): void {
    logger.info('视频播放器打开2', id, ids)
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

  function show(id: number): void {
    currentId.value = id
    selection.select(id)
  }


  return { visible, playlistIds, currentId, open, close }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useVideoPlayerStore, import.meta.hot))
}
