import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useSelectionStore } from '@/application/stores/selection'
import type { ResourceBatchAction } from '@/infrastructure/http'

export type ShellBatchContext = 'browse' | 'trash'

type ShellBatchBindings = {
  emptyTrash: () => Promise<void>
  runBatch: (
    action: ResourceBatchAction,
    tagNames?: string[],
    categoryIds?: number[],
    characterIds?: number[],
    personIds?: number[],
  ) => Promise<boolean>
}

export const useShellBatchStore = defineStore('shellBatch', () => {
  const selection = useSelectionStore()
  const bound = ref(false)
  const context = ref<ShellBatchContext>('browse')
  const total = ref(0)
  const busy = ref(false)
  const message = ref('')
  const batchMode = ref(false)
  let bindings: ShellBatchBindings | null = null
  let generation = 0

  const selectedCount = computed(() => selection.selectedIds.length)
  const showCluster = computed(() => bound.value && (total.value > 0 || batchMode.value))

  function bind(next: { context: ShellBatchContext } & ShellBatchBindings): void {
    bindings = { emptyTrash: next.emptyTrash, runBatch: next.runBatch }
    bound.value = true
    context.value = next.context
  }

  function setTotal(value: number): void {
    total.value = value
  }

  function unbind(): void {
    generation += 1
    batchMode.value = false
    bound.value = false
    total.value = 0
    busy.value = false
    message.value = ''
    bindings = null
    selection.clear()
  }

  function isLive(ticket: number): boolean {
    return bound.value && ticket === generation
  }

  function ticket(): number {
    return generation
  }

  function enter(): void {
    message.value = ''
    selection.clear()
    batchMode.value = true
  }

  function exit(): void {
    batchMode.value = false
    selection.clear()
  }

  async function emptyTrash(): Promise<void> {
    await bindings?.emptyTrash()
  }

  async function runBatch(
    action: ResourceBatchAction,
    tagNames?: string[],
    categoryIds?: number[],
    characterIds?: number[],
    personIds?: number[],
  ): Promise<boolean> {
    return (await bindings?.runBatch(action, tagNames, categoryIds, characterIds, personIds)) ?? false
  }

  return {
    bound,
    context,
    total,
    busy,
    message,
    batchMode,
    selectedCount,
    showCluster,
    bind,
    setTotal,
    unbind,
    ticket,
    isLive,
    enter,
    exit,
    emptyTrash,
    runBatch,
  }
})
