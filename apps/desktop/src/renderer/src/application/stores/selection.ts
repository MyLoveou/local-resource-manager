/**
 * 当前选中的资源（中间栏单击 → 右侧 InfoPanel）。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSelectionStore = defineStore('selection', () => {
  const selectedId = ref<number | null>(null)

  function select(id: number): void {
    selectedId.value = id
  }

  function clear(): void {
    selectedId.value = null
  }

  return { selectedId, select, clear }
})
