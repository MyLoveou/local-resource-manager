/**
 * 导入向导：选类型 → 选文件/目录 → 轮询后端 job。
 */
import { ref } from 'vue'
import { createImport, getImportJob } from '@/infrastructure/http'
import type { ImportJob, ImportSourceKind } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import {
  ENABLED_IMPORT_TYPES,
  IMPORT_POLL_INTERVAL_MS,
  SourceKind,
  fileFilterForResourceType,
} from '@/domain'
import type { ResourceType } from '@/domain'

export { ENABLED_IMPORT_TYPES }

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function useLibraryImport() {
  const library = useLibraryStore()
  const visible = ref(false)
  const step = ref<'type' | 'source' | 'progress'>('type')
  const resourceType = ref<ResourceType>('image')
  const sourceKind = ref<ImportSourceKind>(SourceKind.FILE)
  const job = ref<ImportJob | null>(null)
  const busy = ref(false)
  const picking = ref(false)
  const errorMessage = ref('')

  function open(): void {
    visible.value = true
    step.value = 'type'
    job.value = null
    errorMessage.value = ''
    busy.value = false
  }

  function close(): void {
    if (busy.value) return
    visible.value = false
  }

  function goSource(): void {
    step.value = 'source'
  }

  async function pickAndImport(): Promise<void> {
    if (busy.value || picking.value) return
    picking.value = true
    errorMessage.value = ''
    const filter = fileFilterForResourceType(resourceType.value)
    if (!filter) {
      errorMessage.value = '不支持的资源类型'
      picking.value = false
      return
    }
    let paths: string[] = []
    try {
      const pickers: Record<SourceKind, () => Promise<string[]>> = {
        [SourceKind.FILE]: async () => (await window.electron.selectFiles([filter])) ?? [],
        [SourceKind.DIRECTORY]: async () => {
          const dir = await window.electron.selectDirectory()
          return dir ? [dir] : []
        },
      }
      paths = await pickers[sourceKind.value]()
      if (paths.length === 0) return
    } catch {
      errorMessage.value = '无法打开文件选择框'
      step.value = 'progress'
      return
    } finally {
      picking.value = false
    }

    busy.value = true
    step.value = 'progress'
    try {
      const created = await createImport({
        type: resourceType.value,
        sourceKind: sourceKind.value,
        paths,
      })
      let current = await getImportJob(created.jobId)
      job.value = current
      while (current.status === 'queued' || current.status === 'running') {
        await sleep(IMPORT_POLL_INTERVAL_MS)
        current = await getImportJob(created.jobId)
        job.value = current
      }
      if (current.status === 'done') {
        library.bump(resourceType.value)
      } else {
        errorMessage.value = current.error || '导入失败'
      }
    } catch (err) {
      const status = (err as { response?: { status?: number; data?: { detail?: string } } }).response
      if (status?.status === 409) {
        errorMessage.value = '正在导入，请稍候'
      } else {
        errorMessage.value = status?.data?.detail || '导入失败'
      }
    } finally {
      busy.value = false
    }
  }

  return {
    visible,
    step,
    resourceType,
    sourceKind,
    job,
    busy,
    errorMessage,
    open,
    close,
    goSource,
    pickAndImport,
  }
}
