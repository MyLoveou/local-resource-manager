export type TimelineScope = 'image' | 'video' | 'media'

export interface CategoryRule {
  include: number[]
  exclude: number[]
}

export interface SavedViewFilters {
  image: CategoryRule
  video: CategoryRule
  tagIds: number[]
  dateFrom?: string | null
  dateTo?: string | null
  includeUntimed: boolean
}

export interface SavedView {
  id: number
  kind: 'timeline'
  scope: TimelineScope
  name: string
  filters: SavedViewFilters
  sort: string
  createdAt?: string | null
  updatedAt?: string | null
}
