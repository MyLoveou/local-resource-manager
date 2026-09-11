/**
 * 库变更通知：导入成功后自增。
 * 类型页只应在 importedType 与本页 type 一致时重拉。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ResourceType } from '@/domain'

export const useLibraryStore = defineStore('library', () => {
  const revision = ref(0)
  const importedType = ref<ResourceType | null>(null)

  function bump(type: ResourceType): void {
    importedType.value = type
    revision.value += 1
  }

  return { revision, importedType, bump }
})
