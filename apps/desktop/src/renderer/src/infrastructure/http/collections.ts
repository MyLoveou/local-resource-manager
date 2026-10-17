/**
 * 合集端点（infrastructure/http · 后端 /library/collections）
 */
import client from './client'
import type { Collection, Resource } from '@/domain'

export async function listCollections(): Promise<Collection[]> {
  const { data } = await client.get<{ items: Collection[] }>('/library/collections')
  return data.items
}

export async function getCollection(id: number): Promise<Collection> {
  const { data } = await client.get<Collection>(`/library/collections/${id}`)
  return data
}

export async function createCollection(body: {
  title: string
  description?: string
}): Promise<Collection> {
  const { data } = await client.post<Collection>('/library/collections', body)
  return data
}

export async function patchCollection(
  id: number,
  body: { title?: string; description?: string },
): Promise<Collection> {
  const { data } = await client.patch<Collection>(`/library/collections/${id}`, body)
  return data
}

export async function deleteCollection(id: number): Promise<void> {
  await client.delete(`/library/collections/${id}`)
}

export async function collectionMembers(id: number): Promise<Resource[]> {
  const { data } = await client.get<Resource[]>(`/library/collections/${id}/items`)
  return data
}

export async function addCollectionItem(id: number, resourceId: number): Promise<void> {
  await client.post(`/library/collections/${id}/items`, { resourceId })
}

export async function removeCollectionItem(id: number, resourceId: number): Promise<void> {
  await client.delete(`/library/collections/${id}/items/${resourceId}`)
}

export async function moveCollectionItem(
  id: number,
  resourceId: number,
  direction: 'up' | 'down',
): Promise<void> {
  await client.post(`/library/collections/${id}/items/${resourceId}/move`, { direction })
}

export async function resourceCollections(resourceId: number): Promise<Collection[]> {
  const { data } = await client.get<{ items: Collection[] }>(
    `/library/resources/${resourceId}/collections`,
  )
  return data.items
}
