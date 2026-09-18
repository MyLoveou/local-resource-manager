/**
 * 音频 overlay 状态。
 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'
import { useSelectionStore } from './selection'

export const useAudioPlayerStore = defineStore('audioPlayer', () => {
  const visible = ref(false)
  const playlistIds = ref<number[]>([])
  const currentId = ref<number | null>(null)
  const selection = useSelectionStore()

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

  return { visible, playlistIds, currentId, open, close }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAudioPlayerStore, import.meta.hot))
}
