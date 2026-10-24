/**
 * 分类/标签词表只读列表（随资源保存创建词条，无管理 CRUD）。
 * getTags(type)：给类型时只拉该类型实际打过的标签（本类标签筛选）。
 */
import client from './client'
import type { Category, ResourceType, Tag } from '@/domain'

let categoryCache: Category[] | null = null
let categoryInflight: Promise<Category[]> | null = null
const tagCache = new Map<string, Tag[]>()

export async function getCategories(): Promise<Category[]> {
  if (categoryCache) return categoryCache
  if (categoryInflight) return categoryInflight
  categoryInflight = client
    .get<{ items: Category[] }>('/library/categories')
    .then(({ data }) => {
      categoryCache = data.items
      return data.items
    })
    .finally(() => {
      categoryInflight = null
    })
  return categoryInflight
}

export function invalidateCategories(): void {
  categoryCache = null
}

export async function getTags(type?: ResourceType): Promise<Tag[]> {
  const key = type ?? ''
  const hit = tagCache.get(key)
  if (hit) return hit
  const { data } = await client.get<{ items: Tag[] }>(
    '/library/tags',
    type ? { params: { type } } : undefined
  )
  tagCache.set(key, data.items)
  return data.items
}

export function invalidateTags(): void {
  tagCache.clear()
}
