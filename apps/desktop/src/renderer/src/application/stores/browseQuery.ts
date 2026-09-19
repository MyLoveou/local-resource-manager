import { defineStore } from 'pinia'
import { ref } from 'vue'
import 'pinia-plugin-persistedstate'
import { allowedSortKeys, type ResourceStatus, type ResourceType } from '@/domain'

export type BrowseSession = {
  q: string
  sort: string
  order: 'asc' | 'desc'
  tagIds: number[]
}

function defaultSession(): BrowseSession {
  return { q: '', sort: 'createdAt', order: 'desc', tagIds: [] }
}

export function browseScopeKey(type?: ResourceType, status?: ResourceStatus): string {
  if (status === 'trashed') return 'scope:trash'
  if (!type) return 'scope:all'
  return `type:${type}`
}

export const useBrowseQueryStore = defineStore(
  'browseQuery',
  () => {
    const sessions = ref<Record<string, BrowseSession>>({})

    function ensure(type?: ResourceType, status?: ResourceStatus): BrowseSession {
      const key = browseScopeKey(type, status)
      if (!sessions.value[key]) {
        sessions.value[key] = defaultSession()
      }
      const current = sessions.value[key]
      const allowed = allowedSortKeys(status === 'trashed' ? undefined : type)
      if (!allowed.includes(current.sort)) {
        current.sort = 'createdAt'
      }
      return current
    }

    function patch(type: ResourceType | undefined, status: ResourceStatus | undefined, partial: Partial<BrowseSession>): void {
      const key = browseScopeKey(type, status)
      const current = ensure(type, status)
      sessions.value[key] = { ...current, ...partial }
    }

    return { sessions, ensure, patch }
  },
  { persist: { pick: ['sessions'] } }
)
