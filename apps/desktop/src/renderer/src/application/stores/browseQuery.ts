import { defineStore } from 'pinia'
import { ref } from 'vue'
import 'pinia-plugin-persistedstate'
import {
  allowedSortKeys,
  type ResourceStatus,
  type ResourceType,
  type ViewMode,
} from '@/domain'

export type BrowseSession = {
  q: string
  sort: string
  order: 'asc' | 'desc'
  tagIds: number[]
  categoryIds: number[]
  uncategorized: boolean
  view: ViewMode
  savedViewId: number | null
  /** 主库默认隐藏合集成员；true 时显示 */
  includeCollected: boolean
}

export function defaultSession(): BrowseSession {
  return {
    q: '',
    sort: 'createdAt',
    order: 'desc',
    tagIds: [],
    categoryIds: [],
    uncategorized: false,
    view: 'grid',
    savedViewId: null,
    includeCollected: false,
  }
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
      // 兼容旧持久化数据
      if (!Array.isArray(current.categoryIds)) current.categoryIds = []
      if (current.uncategorized === undefined) current.uncategorized = false
      if (!current.view) current.view = 'grid'
      if (current.savedViewId === undefined) current.savedViewId = null
      const allowed = allowedSortKeys(status === 'trashed' ? undefined : type)
      if (!allowed.includes(current.sort)) {
        current.sort = 'createdAt'
      }
      return current
    }

    function patch(
      type: ResourceType | undefined,
      status: ResourceStatus | undefined,
      partial: Partial<BrowseSession>,
    ): void {
      const key = browseScopeKey(type, status)
      const current = ensure(type, status)
      sessions.value[key] = { ...current, ...partial }
    }

    function reset(
      type: ResourceType | undefined,
      status: ResourceStatus | undefined,
      keepView = true,
    ): void {
      const key = browseScopeKey(type, status)
      const previousView = sessions.value[key]?.view ?? 'grid'
      sessions.value[key] = {
        ...defaultSession(),
        view: keepView ? previousView : 'grid',
      }
    }

    return { sessions, ensure, patch, reset }
  },
  { persist: { pick: ['sessions'] } }
)
