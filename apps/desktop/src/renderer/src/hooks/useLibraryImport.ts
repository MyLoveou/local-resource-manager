/**
 * 导入向导：选类型 → 选文件/目录 → 轮询后端 job。
 */
import { ref } from 'vue'
import { createImport, getImportJob } from '@/infrastructure/http'
import type { ImportJob, ImportSourceKind } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { ResourceType } from '@/domain'

const IMAGE_FILTER = {
  name: '图片',
  extensions: ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'avif'],
}
const VIDEO_FILTER = {
  name: '视频',
  extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'ts', 'm4v'],
}

export const ENABLED_IMPORT_TYPES: { value: ResourceType; label: string }[] = [
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
]

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function useLibraryImport() {
  const library = useLibraryStore()
  const visible = ref(false)
  const step = ref<'type' | 'source' | 'progress'>('type')
  const resourceType = ref<ResourceType>('image')
  const sourceKind = ref<ImportSourceKind>('file')
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
    const filter = resourceType.value === 'image' ? IMAGE_FILTER : VIDEO_FILTER
    let paths: string[] = []
    try {
      if (sourceKind.value === 'file') {
        paths = (await window.electron.selectFiles([filter])) ?? []
        if (paths.length === 0) return
      } else {
        const dir = await window.electron.selectDirectory()
        if (!dir) return
        paths = [dir]
      }
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
        await sleep(300)
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
