import client from './client'
import type { CategoryNode, ResourceType } from '@/domain'

/**
 * 分类树只由 Pinia categoryTree store 缓存。
 * HTTP 层不再维护第二份树缓存，避免 force 刷新仍读到旧计数。
 */
export async function getCategoryTree(type: ResourceType): Promise<CategoryNode[]> {
  const { data } = await client.get<{ items: CategoryNode[] }>('/library/categories', {
    params: { type },
  })
  return data.items
}

export async function createCategory(body: {
  type: ResourceType
  parentId?: number | null
  name: string
  sort?: number
}): Promise<CategoryNode[]> {
  const { data } = await client.post<{ items: CategoryNode[] }>('/library/categories', body)
  return data.items
}

export async function patchCategory(
  id: number,
  type: ResourceType,
  body: { name?: string; parentId?: number | null; sort?: number },
): Promise<CategoryNode[]> {
  const { data } = await client.patch<{ items: CategoryNode[] }>(
    `/library/categories/${id}`,
    body,
  )
  return data.items
}

export async function deleteCategory(id: number): Promise<void> {
  await client.delete(`/library/categories/${id}`)
}
