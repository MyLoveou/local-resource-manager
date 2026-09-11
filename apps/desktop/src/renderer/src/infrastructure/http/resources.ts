/**
 * 资源列表端点（infrastructure/http · 后端 /library/resources）
 */
import client from './client'
import type { ResourcePage, ResourcePageQuery, Resource } from '@/domain'

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
  if (Array.isArray(data) || !data || !Array.isArray(data.items)) {
    throw new Error('资源列表接口已改为分页，请重启桌面端以加载新后端')
  }
  return data
}

export async function getResource(resourceId: number) {
  const { data } = await client.get<Resource>(`/library/resources/${resourceId}`)
  return data
}