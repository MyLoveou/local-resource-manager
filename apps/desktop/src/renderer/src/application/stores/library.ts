/**
 * 库变更通知：导入/删除后自增。importedType 为空时所有列表重拉。
 * bump：手动导入等需要重置到首页的场景；
 * watchBump：监视目录自动导入，页面软刷新（保留浏览位置，只插入新项）。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ResourceType } from '@/domain'

export const useLibraryStore = defineStore('library', () => {
  const revision = ref(0)
  const importedType = ref<ResourceType | null>(null)
  const watchRevision = ref(0)
  const watchType = ref<ResourceType | null>(null)

  function bump(type: ResourceType | null = null): void {
    importedType.value = type
    revision.value += 1
  }

  function watchBump(type: ResourceType): void {
    watchType.value = type
    watchRevision.value += 1
  }

  return { revision, importedType, watchRevision, watchType, bump, watchBump }
})
