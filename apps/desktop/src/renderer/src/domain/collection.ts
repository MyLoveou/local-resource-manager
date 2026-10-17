/**
 * 合集类型（与后端 /library/collections 契约对齐）
 */

/** 全库混排里的合集卡 */
export interface CollectionCardData {
  cardType: 'collection'
  id: number
  title: string
  memberCount: number
  updatedAt?: string | null
  thumbnailPath?: string | null
}

/** 合集 */
export interface Collection {
  id: number
  title: string
  description?: string | null
  memberCount: number
  createdAt?: string | null
  updatedAt?: string | null
}

/** 判别混排条目是否为合集卡 */
export function isCollectionCard(item: unknown): item is CollectionCardData {
  return (
    !!item &&
    typeof item === 'object' &&
    (item as { cardType?: unknown }).cardType === 'collection'
  )
}
