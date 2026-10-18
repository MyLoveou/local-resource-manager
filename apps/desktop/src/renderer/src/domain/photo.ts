/** 照片时间线（后端 /library/photos） */

export interface PhotoTile {
  id: number
  title: string
  kind: 'image' | 'video'
  width?: number | null
  height?: number | null
  duration?: number | null
  thumbnailPath?: string | null
  takenAt?: string | null
}

export interface PhotoTimelineDay {
  date: string
  count: number
  photos: PhotoTile[]
}

export interface PhotoTimeline {
  days: PhotoTimelineDay[]
  unknownCount: number
  unknownPhotos: PhotoTile[]
  total: number
}

export interface PhotoBackfillResult {
  scanned: number
  takenAtUpdated: number
  gpsUpdated: number
  skipped: number
  failed: number
}
