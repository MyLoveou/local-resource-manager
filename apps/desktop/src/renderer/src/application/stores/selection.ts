/**
 * 当前选中的资源（单击单选；Ctrl 切换；Shift 范围）。
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useSelectionStore = defineStore('selection', () => {
  const selectedIds = ref<number[]>([])
  const anchorId = ref<number | null>(null)
  const activeId = ref<number | null>(null)
  /** 系列详情里选中的季；面板据此切换 */
  const season = ref<number | null>(null)

  const selectedId = computed(() => activeId.value)

  function select(id: number): void {
    selectedIds.value = [id]
    anchorId.value = id
    activeId.value = id
  }

  function toggle(id: number): void {
    const has = selectedIds.value.includes(id)
    selectedIds.value = has ? selectedIds.value.filter((item) => item !== id) : [...selectedIds.value, id]
    anchorId.value = id
    activeId.value = selectedIds.value.includes(id) ? id : (selectedIds.value.at(-1) ?? null)
  }

  function selectRange(orderedIds: number[], toId: number): void {
    const from = anchorId.value ?? toId
    const start = orderedIds.indexOf(from)
    const end = orderedIds.indexOf(toId)
    if (start < 0 || end < 0) {
      select(toId)
      return
    }
    const lo = Math.min(start, end)
    const hi = Math.max(start, end)
    selectedIds.value = orderedIds.slice(lo, hi + 1)
    if (anchorId.value === null) {
      anchorId.value = from
    }
    activeId.value = toId
  }

  function setSelection(ids: number[]): void {
    const unique = [...new Set(ids)]
    selectedIds.value = unique
    anchorId.value = unique[0] ?? null
    activeId.value = unique.at(-1) ?? null
  }

  function selectSeason(next: number | null): void {
    season.value = next
  }

  function clear(): void {
    selectedIds.value = []
    anchorId.value = null
    activeId.value = null
  }

  return {
    selectedIds,
    selectedId,
    anchorId,
    season,
    select,
    toggle,
    selectRange,
    setSelection,
    selectSeason,
    clear,
  }
})
