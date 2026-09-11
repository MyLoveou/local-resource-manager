/**
 * 资源列表端点（infrastructure/http · 后端 /library/resources）
 */
import client from './client'
import type { ResourcePage, ResourcePageQuery, Resource } from '@/domain'

/** 资源部分更新（与后端 ResourcePatch 对齐） */
export interface ResourcePatch {
  title?: string | null
  description?: string | null
  rating?: number | null
  categoryName?: string | null
  tagNames?: string[]
}

/** 分页获取资源 */
export async function getResources(query: ResourcePageQuery = {}): Promise<ResourcePage> {
  const { data } = await client.get<ResourcePage>('/library/resources', {
    params: {
      type: query.type,
      status: query.status,
      limit: query.limit,
      offset: query.offset,
      sort: query.sort,
      order: query.order,
    },
  })
  return data
}

export async function getResource(resourceId: number): Promise<Resource> {
  const { data } = await client.get<Resource>(`/library/resources/${resourceId}`)
  return data
}

export async function patchResource(resourceId: number, patch: ResourcePatch): Promise<Resource> {
  const { data } = await client.patch<Resource>(`/library/resources/${resourceId}`, patch)
  return data
}

export async function postResourceCover(resourceId: number, path: string): Promise<Resource> {
  const { data } = await client.post<Resource>(`/library/resources/${resourceId}/cover`, { path })
  return data
}

export async function deleteResource(resourceId: number): Promise<Resource> {
  const { data } = await client.delete<Resource>(`/library/resources/${resourceId}`)
  return data
}
