/**
 * 照片时间线端点（infrastructure/http · 后端 /library/photos）
 */
import client from './client'
import type { PhotoBackfillResult, PhotoTimeline } from '@/domain'

export async function getPhotoTimeline(params: {
  includeAll?: boolean
  year?: number
  month?: number
  categoryId?: number | null
  tagIds?: number[]
}): Promise<PhotoTimeline> {
  const { data } = await client.get<PhotoTimeline>('/library/photos/timeline', {
    params: {
      includeAll: params.includeAll,
      year: params.year,
      month: params.month,
      categoryId: params.categoryId,
      tagIds: params.tagIds,
    },
  })
  return data
}

export async function backfillPhotos(): Promise<PhotoBackfillResult> {
  const { data } = await client.post<PhotoBackfillResult>('/library/photos/backfill')
  return data
}
