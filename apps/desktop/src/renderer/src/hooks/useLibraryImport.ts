/**
 * 导入向导：选类型 → 选文件/目录 → 轮询后端 job。
 */
import { computed, ref } from 'vue'
import { createImport, getCategoryTree, getImportJob, getTags, invalidateTags, previewImport } from '@/infrastructure/http'
import type { ImportPreview } from '@/infrastructure/http'
import type { ImportJob, ImportSourceKind } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import {
  ENABLED_IMPORT_TYPES,
  IMPORT_POLL_INTERVAL_MS,
  SourceKind,
  fileFilterForResourceType,
  DEFAULT_IMPORT_SOURCE_KIND,
  allowsFileSource,
  profileFor,
  flattenCategoryTree,
  type StorageKind,
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
  const storageKind = ref<StorageKind>('owned')
  const timelineVisible = ref(true)
  const mapVisible = ref(true)
  const categoryIds = ref<number[]>([])
  const tagIds = ref<number[]>([])
  const categoryOptions = ref<{ label: string; value: number }[]>([])
  const tagOptions = ref<{ label: string; value: number }[]>([])
  const tagNamesById = ref(new Map<number, string>())
  const job = ref<ImportJob | null>(null)
  const busy = ref(false)
  const preview = ref<ImportPreview | null>(null)
  const picking = ref(false)
  const errorMessage = ref('')
  const allowsMultipleStorage = computed(
    () => (profileFor(resourceType.value)?.allowedStorage.length ?? 1) > 1
  )

  function open(): void {
    visible.value = true
    step.value = 'type'
    job.value = null
    errorMessage.value = ''
    categoryIds.value = []
    tagIds.value = []
    timelineVisible.value = true
    mapVisible.value = true
    busy.value = false
  }

  function close(): void {
    if (busy.value) return
    visible.value = false
  }

  async function loadMeta(): Promise<void> {
    try {
      const [tree, tags] = await Promise.all([
        getCategoryTree(resourceType.value),
        getTags(resourceType.value),
      ])
      categoryOptions.value = flattenCategoryTree(tree).map((node) => ({
        label: node.name,
        value: node.id,
      }))
      tagOptions.value = tags.flatMap((tag) =>
        tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
      )
      tagNamesById.value = new Map(
        tags.flatMap((tag) => (tag.id === undefined ? [] : [[tag.id, tag.name] as const]))
      )
    } catch (error) {
      console.error(error)
    }
  }

  function goSource(): void {
    const profile = profileFor(resourceType.value)
    sourceKind.value = DEFAULT_IMPORT_SOURCE_KIND[resourceType.value]
    storageKind.value = profile?.defaultStorage ?? 'owned'
    step.value = 'source'
    void loadMeta()
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
    let paths: string[]
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
        storageKind: storageKind.value,
        timelineVisible:
          (resourceType.value === 'image' || resourceType.value === 'video') &&
          !timelineVisible.value
            ? false
            : undefined,
        mapVisible:
          (resourceType.value === 'image' || resourceType.value === 'video') &&
          !mapVisible.value
            ? false
            : undefined,
        categoryIds: categoryIds.value.length ? categoryIds.value : undefined,
        tagNames: tagIds.value.length
          ? tagIds.value.flatMap((id) => {
              const name = tagNamesById.value.get(id)
              return name ? [name] : []
            })
          : undefined,
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
        invalidateTags()
        library.invalidate({
          resources: [resourceType.value],
          categories: [resourceType.value],
          tags: true,
          home: true,
        })
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

  /** 预览：只算结构，不写盘。番剧/AV 的整目录导入才有意义。 */
  async function previewStructure(): Promise<void> {
    const dir = await window.electron.selectDirectory()
    if (!dir) return
    busy.value = true
    errorMessage.value = ''
    try {
      preview.value = await previewImport({ type: resourceType.value, path: dir })
    } catch {
      errorMessage.value = '预览失败'
      preview.value = null
    } finally {
      busy.value = false
    }
  }

  return {
    visible,
    step,
    resourceType,
    sourceKind,
    storageKind,
    timelineVisible,
    mapVisible,
    categoryIds,
    tagIds,
    categoryOptions,
    tagOptions,
    job,
    busy,
    errorMessage,
    allowsFileSource,
    allowsMultipleStorage,
    open,
    close,
    goSource,
    pickAndImport,
    preview,
    previewStructure,
  }
}
