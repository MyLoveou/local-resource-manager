import client from './client'
import type { SubtitleTrack } from '@/domain/subtitle'

export interface BackfillResult {
  generated: number
  skipped: number
  failed: number
}

interface SubtitleItemDto {
  id: number
  episodeId?: number | null
  fileId: number
  label: string
  language?: string | null
  renderable: boolean
  format?: string | null
  url: string
}

function toTrack(item: SubtitleItemDto): SubtitleTrack {
  return {
    id: item.id,
    episodeId: item.episodeId ?? null,
    url: item.url,
    label: item.label,
    language: item.language ?? null,
    renderable: item.renderable,
    format: item.format ?? null,
  }
}

export async function getSubtitles(resourceId: number): Promise<SubtitleTrack[]> {
  const { data } = await client.get<SubtitleItemDto[]>(
    `/library/resources/${resourceId}/subtitles`,
  )
  return data.map(toTrack)
}

export async function attachSubtitle(
  resourceId: number,
  filePath: string,
  episodeId?: number | null,
): Promise<SubtitleTrack> {
  const { data } = await client.post<SubtitleItemDto>(
    `/library/resources/${resourceId}/subtitles`,
    { filePath, episodeId: episodeId ?? null },
  )
  return toTrack(data)
}

export async function detachSubtitle(trackId: number): Promise<void> {
  await client.delete(`/library/subtitles/${trackId}`)
}

export async function backfillCovers(
  resourceId: number,
  force = false,
): Promise<BackfillResult> {
  const { data } = await client.post<BackfillResult>(
    `/library/resources/${resourceId}/covers/backfill`,
    null,
    { params: { force } },
  )
  return data
}
