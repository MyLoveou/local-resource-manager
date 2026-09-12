/**
 * 库变更通知：导入/删除后自增。importedType 为空时所有列表重拉。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ResourceType } from '@/domain'

export const useLibraryStore = defineStore('library', () => {
  const revision = ref(0)
  const importedType = ref<ResourceType | null>(null)

  function bump(type: ResourceType | null = null): void {
    importedType.value = type
    revision.value += 1
  }

  return { revision, importedType, bump }
})
