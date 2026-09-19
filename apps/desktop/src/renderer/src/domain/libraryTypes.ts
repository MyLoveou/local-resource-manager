/**
 * 类型能力目录（与后端 type_profile 字段同名；扩展名去点）。
 */
import type { ResourceType } from './resource'
import { SourceKind } from './constants'

export type IngestKind = 'file' | 'series' | 'package'
export type ConsumeKind =
  | 'overlay-image'
  | 'overlay-video'
  | 'overlay-audio'
  | 'overlay-series'
  | 'overlay-model'
  | 'shell-open'
export type StorageKind = 'owned' | 'indexed'

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
export const AUDIO_EXTENSIONS = ['mp3', 'flac', 'wav', 'aac', 'ogg', 'm4a', 'wma', 'opus'] as const
export const NOVEL_EXTENSIONS = ['epub', 'pdf', 'txt', 'html', 'htm', 'mobi', 'azw3'] as const
export const GAME_LAUNCH_EXTENSIONS = ['exe', 'bat', 'cmd', 'lnk'] as const
export const MODEL_EXTENSIONS = ['gltf', 'glb', 'obj', 'fbx', 'stl'] as const
export const MODEL_PREVIEW_EXTENSIONS = ['gltf', 'glb'] as const
export const COMIC_ARCHIVE_EXTENSIONS = ['cbz', 'cbr'] as const

export interface TypeProfile {
  type: ResourceType
  label: string
  emptyHint: string
  routePath: string
  routeIcon: string
  ingestKind: IngestKind
  consumeKind: ConsumeKind
  defaultSource: SourceKind
  defaultStorage: StorageKind
  allowedStorage: readonly StorageKind[]
  extensions: readonly string[]
  coverFallback: boolean
  allowsFileSource: boolean
  allowsUserCover: boolean
  searchKeys?: readonly string[]
  sortKeys?: readonly string[]
}

export const TYPE_PROFILES: readonly TypeProfile[] = [
  {
    type: 'image',
    label: '图片',
    emptyHint: '暂无图片，请先在顶栏导入',
    routePath: '/image',
    routeIcon: 'image',
    ingestKind: 'file',
    consumeKind: 'overlay-image',
    defaultSource: SourceKind.FILE,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: IMAGE_EXTENSIONS,
    coverFallback: true,
    allowsFileSource: true,
    allowsUserCover: false,
    searchKeys: ['format'],
    sortKeys: ['width', 'height', 'pixelArea', 'takenAt'],
  },
  {
    type: 'video',
    label: '视频',
    emptyHint: '暂无视频，请先在顶栏导入',
    routePath: '/video',
    routeIcon: 'video',
    ingestKind: 'file',
    consumeKind: 'overlay-video',
    defaultSource: SourceKind.FILE,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: VIDEO_EXTENSIONS,
    coverFallback: false,
    allowsFileSource: true,
    allowsUserCover: true,
    searchKeys: ['format'],
    sortKeys: ['duration', 'resolution', 'bitrate'],
  },
  {
    type: 'anime',
    label: '番剧',
    emptyHint: '暂无番剧，请先在顶栏导入文件夹',
    routePath: '/anime',
    routeIcon: 'anime',
    ingestKind: 'series',
    consumeKind: 'overlay-series',
    defaultSource: SourceKind.DIRECTORY,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: VIDEO_EXTENSIONS,
    coverFallback: true,
    allowsFileSource: false,
    allowsUserCover: true,
    sortKeys: ['episodeCount'],
  },
  {
    type: 'av',
    label: 'AV',
    emptyHint: '暂无 AV，请先在顶栏导入文件夹',
    routePath: '/av',
    routeIcon: 'av',
    ingestKind: 'series',
    consumeKind: 'overlay-series',
    defaultSource: SourceKind.DIRECTORY,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: VIDEO_EXTENSIONS,
    coverFallback: true,
    allowsFileSource: false,
    allowsUserCover: true,
    sortKeys: ['episodeCount'],
  },
  {
    type: 'audio',
    label: '音频',
    emptyHint: '暂无音频，请先在顶栏导入',
    routePath: '/audio',
    routeIcon: 'music',
    ingestKind: 'file',
    consumeKind: 'overlay-audio',
    defaultSource: SourceKind.FILE,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: AUDIO_EXTENSIONS,
    coverFallback: false,
    allowsFileSource: true,
    allowsUserCover: true,
    searchKeys: ['format'],
    sortKeys: ['duration'],
  },
  {
    type: 'novel',
    label: '小说',
    emptyHint: '暂无小说，请先在顶栏导入',
    routePath: '/novel',
    routeIcon: 'book-open-page-variant',
    ingestKind: 'file',
    consumeKind: 'shell-open',
    defaultSource: SourceKind.FILE,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: NOVEL_EXTENSIONS,
    coverFallback: false,
    allowsFileSource: true,
    allowsUserCover: true,
  },
  {
    type: 'game',
    label: '游戏',
    emptyHint: '暂无游戏，请先在顶栏导入文件夹',
    routePath: '/game',
    routeIcon: 'controller-classic',
    ingestKind: 'package',
    consumeKind: 'shell-open',
    defaultSource: SourceKind.DIRECTORY,
    defaultStorage: 'indexed',
    allowedStorage: ['indexed', 'owned'],
    extensions: GAME_LAUNCH_EXTENSIONS,
    coverFallback: false,
    allowsFileSource: false,
    allowsUserCover: true,
    searchKeys: ['path'],
  },
  {
    type: 'model',
    label: '模型',
    emptyHint: '暂无模型，请先在顶栏导入',
    routePath: '/model',
    routeIcon: 'cube-outline',
    ingestKind: 'file',
    consumeKind: 'overlay-model',
    defaultSource: SourceKind.FILE,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: MODEL_EXTENSIONS,
    coverFallback: false,
    allowsFileSource: true,
    allowsUserCover: true,
    searchKeys: ['format'],
  },
  {
    type: 'comic',
    label: '漫画',
    emptyHint: '暂无漫画，请先在顶栏导入文件夹',
    routePath: '/comic',
    routeIcon: 'book-open-blank-variant',
    ingestKind: 'package',
    consumeKind: 'shell-open',
    defaultSource: SourceKind.DIRECTORY,
    defaultStorage: 'owned',
    allowedStorage: ['owned'],
    extensions: [...IMAGE_EXTENSIONS, ...COMIC_ARCHIVE_EXTENSIONS],
    coverFallback: true,
    allowsFileSource: true,
    allowsUserCover: true,
    sortKeys: ['pageCount'],
  },
]

const BY_TYPE = Object.fromEntries(TYPE_PROFILES.map((p) => [p.type, p])) as Record<
  ResourceType,
  TypeProfile
>

export function profileFor(type: ResourceType): TypeProfile | undefined {
  return BY_TYPE[type]
}

export function consumeKindOf(type: ResourceType): ConsumeKind | undefined {
  return BY_TYPE[type]?.consumeKind
}

export const RESOURCE_TYPE_LABEL: Record<ResourceType, string> = Object.fromEntries(
  TYPE_PROFILES.map((p) => [p.type, p.label])
) as Record<ResourceType, string>

export const DEFAULT_IMPORT_SOURCE_KIND: Record<ResourceType, SourceKind> = Object.fromEntries(
  TYPE_PROFILES.map((p) => [p.type, p.defaultSource])
) as Record<ResourceType, SourceKind>

export const SHARED_SORT_KEYS = ['createdAt', 'updatedAt', 'title', 'rating', 'size'] as const

export type ResourceSortKey =
  | (typeof SHARED_SORT_KEYS)[number]
  | 'width'
  | 'height'
  | 'pixelArea'
  | 'takenAt'
  | 'duration'
  | 'resolution'
  | 'bitrate'
  | 'pageCount'
  | 'episodeCount'

export const SORT_LABELS: Record<string, string> = {
  createdAt: '创建时间',
  updatedAt: '更新时间',
  title: '标题',
  rating: '评分',
  size: '体积',
  width: '宽度',
  height: '高度',
  pixelArea: '像素面积',
  takenAt: '拍摄时间',
  duration: '时长',
  resolution: '分辨率',
  bitrate: '码率',
  pageCount: '页数',
  episodeCount: '集数',
}

export function allowedSortKeys(type?: ResourceType | null): string[] {
  if (!type) return [...SHARED_SORT_KEYS]
  return [...SHARED_SORT_KEYS, ...(profileFor(type)?.sortKeys ?? [])]
}
