import client from './client'

export interface AudioTrack {
  index: number
  label: string
  language?: string | null
  codec?: string | null
  channels?: number | null
  url: string
}

export async function getAudioTracks(
  resourceId: number,
  fileId: number,
): Promise<AudioTrack[]> {
  const { data } = await client.get<AudioTrack[]>(
    `/library/resources/${resourceId}/files/${fileId}/audio-tracks`,
  )
  return data
}
