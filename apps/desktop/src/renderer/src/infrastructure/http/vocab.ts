/**
 * 分类/标签词表只读列表（随资源保存创建词条，无管理 CRUD）。
 */
import client from './client'
import type { Category, Tag } from '@/domain'

export async function getCategories(): Promise<Category[]> {
  const { data } = await client.get<{ items: Category[] }>('/library/categories')
  return data.items
}

export async function getTags(): Promise<Tag[]> {
  const { data } = await client.get<{ items: Tag[] }>('/library/tags')
  return data.items
}
