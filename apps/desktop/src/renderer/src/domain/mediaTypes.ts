/**
 * 媒体类型扩展名与对话框过滤映射。
 * 档案在 libraryTypes.ts；本文件再导出兼容旧 import。
 */
import type { ResourceType } from './resource'
import { TYPE_PROFILES, profileFor } from './libraryTypes'

export {
  AUDIO_EXTENSIONS,
  DEFAULT_IMPORT_SOURCE_KIND,
  IMAGE_EXTENSIONS,
  MODEL_PREVIEW_EXTENSIONS,
  RESOURCE_TYPE_LABEL,
  VIDEO_EXTENSIONS,
  consumeKindOf,
  profileFor,
} from './libraryTypes'

export const SUBTITLE_EXTENSIONS = ['srt', 'ass', 'ssa', 'vtt'] as const

export const SERIES_RESOURCE_TYPES: readonly ResourceType[] = TYPE_PROFILES.filter(
  (p) => p.ingestKind === 'series'
).map((p) => p.type)

export interface FileDialogFilter {
  name: string
  extensions: string[]
}

export const RESOURCE_FILE_FILTERS: Record<ResourceType, FileDialogFilter> = Object.fromEntries(
  TYPE_PROFILES.map((p) => [
    p.type,
    { name: p.label, extensions: [...p.extensions] },
  ])
) as Record<ResourceType, FileDialogFilter>

export const SUBTITLE_FILE_FILTER: FileDialogFilter = {
  name: '字幕',
  extensions: [...SUBTITLE_EXTENSIONS],
}

export const COVER_FILE_FILTER: FileDialogFilter = RESOURCE_FILE_FILTERS.image

export const ENABLED_IMPORT_TYPES: { value: ResourceType; label: string }[] = TYPE_PROFILES.map(
  (p) => ({
    value: p.type,
    label: p.label,
  })
)

export const FILE_ROLE = {
  PRIMARY: 'primary',
  COVER: 'cover',
  SUBTITLE: 'subtitle',
  THUMBNAIL: 'thumbnail',
  LAUNCH: 'launch',
  PAGE: 'page',
  EPISODE: 'episode',
  EXTRA: 'extra',
} as const

export const THUMB_DIR = 'thumbs'
export const THUMB_GRID_NAME = 'grid.webp'
export const THUMB_MAX_EDGE_PX = 480
export const THUMB_WEBP_QUALITY = 80

export const IMPORT_POLL_INTERVAL_MS = 300

export function fileFilterForResourceType(type: ResourceType): FileDialogFilter | undefined {
  return RESOURCE_FILE_FILTERS[type]
}

export function isSeriesResourceType(type: ResourceType): boolean {
  return (SERIES_RESOURCE_TYPES as readonly string[]).includes(type)
}

export function allowsFileSource(type: ResourceType): boolean {
  return profileFor(type)?.allowsFileSource === true
}
