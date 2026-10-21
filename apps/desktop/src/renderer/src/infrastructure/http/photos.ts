/**
 * 时间线端点（infrastructure/http → 后端 /library/photos）
 */
import client from './client'
import type { CategoryRule, PhotoBackfillResult, PhotoTimeline, TimelineScope } from '@/domain'

export async function getPhotoTimeline(params: {
  scope: TimelineScope
  includeAll?: boolean
  year?: number
  month?: number
  imageRule?: CategoryRule
  videoRule?: CategoryRule
  tagIds?: number[]
  dateFrom?: string | null
  dateTo?: string | null
  includeUntimed?: boolean
  mapVisible?: boolean
  mapOnly?: boolean
  type?: 'image' | 'video'
  categoryIds?: number[]
}): Promise<PhotoTimeline> {
  const { data } = await client.get<PhotoTimeline>('/library/photos/timeline', {
    params: {
      scope: params.scope,
      type: params.type,
      includeAll: params.includeAll,
      year: params.year,
      month: params.month,
      imageCategoryIds: params.imageRule?.include,
      videoCategoryIds: params.videoRule?.include,
      imageExcludeCategoryIds: params.imageRule?.exclude,
      videoExcludeCategoryIds: params.videoRule?.exclude,
      categoryIds: params.categoryIds,
      tagIds: params.tagIds,
      dateFrom: params.dateFrom,
      dateTo: params.dateTo,
      includeUntimed: params.includeUntimed,
      mapVisible: params.mapVisible,
      mapOnly: params.mapOnly,
    },
  })
  return data
}

export async function backfillPhotos(): Promise<PhotoBackfillResult> {
  const { data } = await client.post<PhotoBackfillResult>('/library/photos/backfill')
  return data
}
