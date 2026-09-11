/**
 * 媒体类型扩展名与对话框过滤映射。
 * 与后端 `app/shared/media_types.py` 对齐（此处无点；后端带点）。
 * 按 ResourceType 查表，禁止调用处 if/else 选过滤表。
 */
import type { ResourceType } from './resource'

export const IMAGE_EXTENSIONS = [
  'jpg',
  'jpeg',
  'png',
  'webp',
  'gif',
  'bmp',
  'heic',
  'avif',
] as const

export const VIDEO_EXTENSIONS = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'ts', 'm4v'] as const

export const SUBTITLE_EXTENSIONS = ['srt', 'ass', 'ssa', 'vtt'] as const

export const RESOURCE_TYPE_LABEL: Record<ResourceType, string> = {
  image: '图片',
  video: '视频',
}

export interface FileDialogFilter {
  name: string
  extensions: string[]
}

export const RESOURCE_FILE_FILTERS: Record<ResourceType, FileDialogFilter> = {
  image: {
    name: RESOURCE_TYPE_LABEL.image,
    extensions: [...IMAGE_EXTENSIONS],
  },
  video: {
    name: RESOURCE_TYPE_LABEL.video,
    extensions: [...VIDEO_EXTENSIONS],
  },
}

export const SUBTITLE_FILE_FILTER: FileDialogFilter = {
  name: '字幕',
  extensions: [...SUBTITLE_EXTENSIONS],
}

export const COVER_FILE_FILTER: FileDialogFilter = RESOURCE_FILE_FILTERS.image

export const ENABLED_IMPORT_TYPES: { value: ResourceType; label: string }[] = (
  Object.keys(RESOURCE_FILE_FILTERS) as ResourceType[]
).map((value) => ({
  value,
  label: RESOURCE_TYPE_LABEL[value],
}))

export const FILE_ROLE = {
  PRIMARY: 'primary',
  COVER: 'cover',
  SUBTITLE: 'subtitle',
} as const

export const IMPORT_POLL_INTERVAL_MS = 300

export function fileFilterForResourceType(type: ResourceType): FileDialogFilter | undefined {
  return RESOURCE_FILE_FILTERS[type]
}
