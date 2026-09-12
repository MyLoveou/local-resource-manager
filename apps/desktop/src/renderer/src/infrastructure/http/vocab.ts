/**
 * 分类/标签词表只读列表（随资源保存创建词条，无管理 CRUD）。
 */
import client from './client'
import type { Category, Tag } from '@/domain'

let categoryCache: Category[] | null = null
let categoryInflight: Promise<Category[]> | null = null

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

export async function getTags(): Promise<Tag[]> {
  const { data } = await client.get<{ items: Tag[] }>('/library/tags')
  return data.items
}
