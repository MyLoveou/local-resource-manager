/**
 * 资源领域类型（与后端 OpenAPI 契约对齐，camelCase）
 * 后端对应：apps/backend/app/shared/models.py
 */

import type { StorageKind } from './libraryTypes'
import type { CharacterBrief } from './character'
import type { PersonBrief } from './person'

/** 资源类型。anime/av 是作品，不是单集。 */
export type ResourceType =
  | 'image'
  | 'video'
  | 'anime'
  | 'av'
  | 'audio'
  | 'novel'
  | 'game'
  | 'model'
  | 'comic'
  | 'work_directory'

/** 资源状态：正常 / 回收站（软删）/ 文件丢失 */
export type ResourceStatus = 'active' | 'trashed' | 'lost'

/** 资源（图片/视频）—— 元数据主体 */
export interface Resource {
  id?: number
  type: ResourceType
  storageKind?: StorageKind
  title: string
  description?: string | null
  /** 作品简介（站点/刮削） */
  synopsis?: string | null
  catalog?: WorkCatalog | null
  /** 评分 0-10 */
  rating?: number | null
  /** 封面本地缓存路径 */
  coverPath?: string | null
  /** 作品封面 URL（已签名）；详情页头部使用 */
  coverUrl?: string | null
  /** 导入时的原始文件名/目录名 */
  sourceName?: string | null
  /** 网格/面板缩略图 URL；展示面禁止回退 coverPath */
  thumbnailPath?: string | null
  status: ResourceStatus
  /** 回收站删除时间 */
  deletedAt?: string | null
  /** 上次元数据抓取时间 */
  lastScrapedAt?: string | null
  /** 抓取来源站点（审计） */
  scrapedSource?: string | null
  /** 站点特有元数据兜底 */
  extra?: Record<string, unknown>
  /** 有未确认的刮削候选 */
  scrapePending?: boolean
  /** 照片时间线：null/undefined=按 EXIF 自动；true/false=手动 */
  timelineVisible?: boolean | null
  mapVisible?: boolean | null
  characters?: CharacterBrief[]
  persons?: PersonBrief[]
  createdAt?: string | null
  updatedAt?: string | null
  /** 资源级作者（自由文本） */
  author?: string | null
  tags?: Tag[]
  files?: ResourceFile[]
  todos?: ResourceTodo[]
  /** 独立分类词条，不是资源 type */
  categories?: Category[]
  /** 仅 anime/av 详情：季集树 */
  seasons?: SeriesSeason[]
  extras?: SeriesExtra[]
}

export interface SeriesEpisode {
  id?: number
  fileId: number
  episodeNumber: number
  title?: string | null
  duration?: number | null
  width?: number | null
  height?: number | null
  /** 每集封面（已签名）；空则回退作品封面 */
  coverUrl?: string | null
  hasCover?: boolean
  /** 是否已挂字幕 */
  hasSubtitles?: boolean
}

export interface SeriesSeason {
  id?: number
  seasonNumber: number
  title?: string | null
  /** 季自己的站点档案（多季作品每季是独立条目） */
  catalog?: WorkCatalog | null
  /** 季封面（已签名）；空则回退作品封面 */
  coverUrl?: string | null
  hasCover?: boolean
  episodes?: SeriesEpisode[]
}

export interface WorkCatalog {
  originalTitle?: string | null
  nameCn?: string | null
  date?: string | null
  platform?: string | null
  eps?: number | null
  totalEpisodes?: number | null
  siteScore?: number | null
  infobox?: Record<string, unknown>[]
  aliases?: string[]
  imageUrls?: string[]
  source?: string | null
  sourceId?: string | null
}

export interface SeriesExtra {
  id?: number
  fileId: number
  title: string
  duration?: number | null
  /** 特典封面（已签名）；空则回退作品封面 */
  coverUrl?: string | null
  hasCover?: boolean
}

/** 资源关联的物理文件（一个资源可含多文件） */
export interface ResourceFile {
  id?: number
  resourceId: number
  path: string
  contentUrl?: string | null
  /** 文件哈希，用于去重与完整性校验 */
  sha256?: string | null
  size?: number | null
  format?: string | null
  role?: string
  /** 视频时长（秒） */
  duration?: number | null
  width?: number | null
  height?: number | null
  /** 视频编码 */
  codec?: string | null
  fps?: number | null
  /** 比特/秒 */
  bitrate?: number | null
  /** 图片拍摄时间（EXIF） */
  exifTakenAt?: string | null
  /** WGS84 纬度 */
  exifLat?: number | null
  /** WGS84 经度 */
  exifLng?: number | null
  /** 机身 */
  exifCamera?: string | null
  /** 镜头 */
  exifLens?: string | null
  exifIso?: number | null
  /** 光圈，如 f/2.8 */
  exifAperture?: string | null
  /** 快门，如 1/125 */
  exifShutter?: string | null
  createdAt?: string | null
}

export interface ResourceTodo {
  id?: number
  resourceId: number
  content: string
  done: boolean
  sort: number
  createdAt?: string | null
}

/** 分类词条（资源单选） */
export interface Category {
  id?: number
  name: string
  type?: ResourceType
  parentId?: number | null
  sort?: number
  isSystem?: boolean
}

/** 标签 */
export interface Tag {
  id?: number
  name: string
}

/** 面板/弹窗共用的未保存草稿（点保存才 PATCH） */
export interface MetadataDraft {
  title: string
  description: string
  synopsis: string
  author: string
  ratingStars: number
  categoryIds: number[]
  tagNames: string[]
  tagInput: string
  pendingCoverPath: string | null
  takenAtLocal: string
}

/** datetime-local 用到分钟；库内存到秒。 */
export function takenAtToLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})/.exec(iso)
  return match?.[1] ?? ''
}

export function localInputToTakenAt(local: string): string | null {
  const text = local.trim()
  if (!text) return null
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(text)) return `${text}:00`
  return text
}

/** 资源列表查询 */
export interface ResourcePageQuery {
  type?: ResourceType
  status?: ResourceStatus
  limit?: number
  offset?: number
  afterCreatedAt?: string | null
  afterId?: number | null
  afterKey?: string | null
  q?: string
  tagIds?: number[]
  categoryId?: number | null
  categoryIds?: number[]
  uncategorized?: boolean
  dateFrom?: string
  dateTo?: string
  takenDate?: string
  untimed?: boolean
  timelineVisible?: boolean
  timelineMedia?: boolean
  mapVisible?: boolean
  mapOnly?: boolean
  characterIds?: number[]
  personIds?: number[]
  /** 主库默认隐藏合集成员；true 时一并返回 */
  includeCollected?: boolean
  sort?: string
  order?: 'asc' | 'desc'
}

/** 资源列表分页信封 */
export interface ResourcePage {
  items: Resource[]
  total: number
  limit: number
  offset: number
  hasMore: boolean
  nextCreatedAt?: string | null
  nextId?: number | null
  nextKey?: string | null
}
