/**
 * 图片查看器覆盖层状态：打开/关闭与当前列表相邻张。
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useSelectionStore } from './selection'

export const useImageViewerStore = defineStore('imageViewer', () => {
  const visible = ref(false)
  const playlistIds = ref<number[]>([])
  const currentId = ref<number | null>(null)
  const selection = useSelectionStore()

  const index = computed(() =>
    currentId.value === null ? -1 : playlistIds.value.indexOf(currentId.value)
  )
  const hasPrev = computed(() => index.value > 0)
  const hasNext = computed(() => index.value >= 0 && index.value < playlistIds.value.length - 1)

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

  function show(id: number): void {
    currentId.value = id
    selection.select(id)
  }

  function prev(): void {
    if (!hasPrev.value) return
    show(playlistIds.value[index.value - 1])
  }

  function next(): void {
    if (!hasNext.value) return
    show(playlistIds.value[index.value + 1])
  }

  return { visible, playlistIds, currentId, hasPrev, hasNext, open, close, prev, next }
})
