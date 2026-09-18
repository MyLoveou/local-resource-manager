/**
 * 模型预览 overlay 状态。
 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'
import { useSelectionStore } from './selection'

export const useModelPreviewStore = defineStore('modelPreview', () => {
  const visible = ref(false)
  const resourceId = ref<number | null>(null)
  const selection = useSelectionStore()

  function open(id: number, _ids?: number[]): void {
    resourceId.value = id
    visible.value = true
    selection.select(id)
  }

  function close(): void {
    visible.value = false
    resourceId.value = null
  }

  return { visible, resourceId, open, close }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useModelPreviewStore, import.meta.hot))
}
