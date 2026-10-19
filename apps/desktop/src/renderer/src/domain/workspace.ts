import type { ResourceType } from './resource'

export type ViewMode = 'grid' | 'timeline' | 'map'

export interface LibraryContext {
  type?: ResourceType
  view: ViewMode
  categoryIds: number[]
  tagIds: number[]
  q: string
  sort: string
  order: 'asc' | 'desc'
  savedViewId: number | null
  includeCollected: boolean
}

export function defaultLibraryContext(type?: ResourceType): LibraryContext {
  return {
    type,
    view: 'grid',
    categoryIds: [],
    tagIds: [],
    q: '',
    sort: 'createdAt',
    order: 'desc',
    savedViewId: null,
    includeCollected: false,
  }
}
