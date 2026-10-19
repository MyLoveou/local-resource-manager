import client from './client'
import type { CategoryNode, ResourceType } from '@/domain'

const treeCache = new Map<string, CategoryNode[]>()

export async function getCategoryTree(type: ResourceType): Promise<CategoryNode[]> {
  const hit = treeCache.get(type)
  if (hit) return hit
  const { data } = await client.get<{ items: CategoryNode[] }>('/library/categories', {
    params: { type },
  })
  treeCache.set(type, data.items)
  return data.items
}

export function invalidateCategoryTree(type?: ResourceType): void {
  if (type) treeCache.delete(type)
  else treeCache.clear()
}

export async function createCategory(body: {
  type: ResourceType
  parentId?: number | null
  name: string
  sort?: number
}): Promise<CategoryNode[]> {
  const { data } = await client.post<{ items: CategoryNode[] }>('/library/categories', body)
  treeCache.set(body.type, data.items)
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
  treeCache.set(type, data.items)
  return data.items
}

export async function deleteCategory(id: number, type: ResourceType): Promise<void> {
  await client.delete(`/library/categories/${id}`)
  treeCache.delete(type)
}
