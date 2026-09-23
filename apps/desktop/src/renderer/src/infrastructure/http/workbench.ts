/**
 * 工作目录、备注、消费记录（/library）
 */
import client from './client'
import { invalidateResourceCache, rememberDetail } from './resources'
import type { Resource } from '@/domain'

export async function createWorkDirectory(path: string): Promise<Resource> {
  const { data } = await client.post<Resource>('/library/work-directories', { path })
  return rememberDetail(data)
}

export async function createWorkNote(
  resourceId: number,
  title: string,
  content: string,
): Promise<Resource> {
  const { data } = await client.post<Resource>(`/library/resources/${resourceId}/notes`, {
    title,
    content,
  })
  invalidateResourceCache(resourceId)
  return rememberDetail(data)
}

export async function deleteWorkNote(resourceId: number, noteId: string): Promise<Resource> {
  const { data } = await client.delete<Resource>(`/library/resources/${resourceId}/notes/${noteId}`)
  invalidateResourceCache(resourceId)
  return rememberDetail(data)
}

export async function postConsumption(resourceId: number, action: string): Promise<void> {
  await client.post('/library/consumptions', { resourceId, action })
}
