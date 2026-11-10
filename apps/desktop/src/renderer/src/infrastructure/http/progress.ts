import client from './client'
import type { PlaybackProgress, PlaybackProgressInput, ResumePage } from '@/domain/progress'

export async function getPlaybackProgress(
  resourceId: number,
  fileId: number,
): Promise<PlaybackProgress | null> {
  const { data } = await client.get<PlaybackProgress | null>(
    `/library/resources/${resourceId}/progress`,
    { params: { fileId } },
  )
  return data
}

export async function putPlaybackProgress(
  resourceId: number,
  body: PlaybackProgressInput,
): Promise<PlaybackProgress | null> {
  const { data } = await client.put<PlaybackProgress | null>(
    `/library/resources/${resourceId}/progress`,
    body,
  )
  return data
}

export async function clearPlaybackProgress(
  resourceId: number,
  fileId?: number,
): Promise<void> {
  await client.delete(`/library/resources/${resourceId}/progress`, {
    params: fileId == null ? {} : { fileId },
  })
}

export async function getResumeList(limit = 20): Promise<ResumePage> {
  const { data } = await client.get<ResumePage>('/library/progress/resume', {
    params: { limit },
  })
  return data
}
