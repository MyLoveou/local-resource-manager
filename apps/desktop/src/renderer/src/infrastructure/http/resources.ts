/**
 * 资源列表端点（infrastructure/http · 后端 /library/resources）
 */
import client from './client'
import type { ResourcePage, ResourcePageQuery, Resource } from '@/domain'

const DETAIL_CACHE_LIMIT = 50
const detailCache = new Map<number, Resource>()

/** 监视导入修订号（后端 /library/watch-revision） */
export interface WatchRevision {
  revision: number
  type: string | null
}

/** 获取监视导入修订号：前端轮询，变化时刷新对应类型列表 */
export async function getWatchRevision(): Promise<WatchRevision> {
  const { data } = await client.get<WatchRevision>('/library/watch-revision')
  return data
}

export function invalidateResourceCache(resourceId?: number): void {
  if (resourceId === undefined) {
    detailCache.clear()
    return
  }
  detailCache.delete(resourceId)
}

export function rememberDetail(row: Resource): Resource {
  if (row.id === undefined) return row
  detailCache.set(row.id, row)
  if (detailCache.size > DETAIL_CACHE_LIMIT) {
    const oldest = detailCache.keys().next().value
    if (typeof oldest === 'number') detailCache.delete(oldest)
  }
  return row
}

/** 资源部分更新（与后端 ResourcePatch 对齐） */
export interface ResourcePatch {
  title?: string | null
  description?: string | null
  synopsis?: string | null
  author?: string | null
  rating?: number | null
  categoryName?: string | null
  tagNames?: string[]
  exifTakenAt?: string | null
}

/** 分页获取资源 */
export async function getResources(query: ResourcePageQuery = {}): Promise<ResourcePage> {
  const { data } = await client.get<ResourcePage>('/library/resources', {
    params: {
      type: query.type,
      status: query.status,
      limit: query.limit,
      offset: query.offset,
      afterCreatedAt: query.afterCreatedAt,
      afterId: query.afterId,
      afterKey: query.afterKey,
      q: query.q,
      tagIds: query.tagIds,
      categoryId: query.categoryId,
      sort: query.sort,
      order: query.order,
    },
  })
  return data
}

export async function getResource(resourceId: number): Promise<Resource> {
  const cached = detailCache.get(resourceId)
  if (cached) return cached
  const { data } = await client.get<Resource>(`/library/resources/${resourceId}`)
  return rememberDetail(data)
}

export async function patchResource(resourceId: number, patch: ResourcePatch): Promise<Resource> {
  const { data } = await client.patch<Resource>(`/library/resources/${resourceId}`, patch)
  return rememberDetail(data)
}

export async function postResourceCover(resourceId: number, path: string): Promise<Resource> {
  const { data } = await client.post<Resource>(`/library/resources/${resourceId}/cover`, { path })
  return rememberDetail(data)
}

export async function postResourceSubtitle(resourceId: number, path: string): Promise<Resource> {
  const { data } = await client.post<Resource>(`/library/resources/${resourceId}/subtitles`, { path })
  return rememberDetail(data)
}

export async function postResourceTodo(resourceId: number, content: string): Promise<Resource> {
  const { data } = await client.post<Resource>(`/library/resources/${resourceId}/todos`, { content })
  return rememberDetail(data)
}

export interface TodoPatch {
  content?: string
  done?: boolean
}

export async function patchResourceTodo(
  resourceId: number,
  todoId: number,
  patch: TodoPatch
): Promise<Resource> {
  const { data } = await client.patch<Resource>(
    `/library/resources/${resourceId}/todos/${todoId}`,
    patch
  )
  return rememberDetail(data)
}

export async function deleteResourceTodo(resourceId: number, todoId: number): Promise<Resource> {
  const { data } = await client.delete<Resource>(`/library/resources/${resourceId}/todos/${todoId}`)
  return rememberDetail(data)
}

export async function deleteResource(resourceId: number): Promise<Resource> {
  const { data } = await client.delete<Resource>(`/library/resources/${resourceId}`)
  return rememberDetail(data)
}

export async function restoreResource(resourceId: number): Promise<Resource> {
  const { data } = await client.post<Resource>(`/library/resources/${resourceId}/restore`)
  return rememberDetail(data)
}

export async function purgeResource(resourceId: number): Promise<{ ok: boolean }> {
  invalidateResourceCache(resourceId)
  const { data } = await client.post<{ ok: boolean }>(`/library/resources/${resourceId}/purge`)
  return data
}

export type ResourceBatchAction = 'trash' | 'restore' | 'purge'

export interface ResourceBatchFailedItem {
  id: number
  message: string
}

export interface ResourceBatchResult {
  ok: number[]
  failed: ResourceBatchFailedItem[]
}

export async function batchResources(
  action: ResourceBatchAction,
  ids: number[],
): Promise<ResourceBatchResult> {
  const { data } = await client.post<ResourceBatchResult>('/library/resources/batch', {
    action,
    ids,
  })
  for (const id of ids) invalidateResourceCache(id)
  return data
}
