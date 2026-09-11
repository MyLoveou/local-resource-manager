/**
 * 资源领域类型（与后端 OpenAPI 契约对齐，camelCase）
 * 后端对应：apps/backend/app/shared/models.py
 */

/** 资源类型（MVP：图片/视频，预留扩展） */
export type ResourceType = 'image' | 'video'

/** 资源状态：正常 / 回收站（软删）/ 文件丢失 */
export type ResourceStatus = 'active' | 'trashed' | 'lost'

/** 资源（图片/视频）—— 元数据主体 */
export interface Resource {
  id?: number
  type: ResourceType
  title: string
  description?: string | null
  /** 评分 0-10 */
  rating?: number | null
  /** 封面本地缓存路径 */
  coverPath?: string | null
  status: ResourceStatus
  /** 回收站删除时间 */
  deletedAt?: string | null
  /** 上次元数据抓取时间 */
  lastScrapedAt?: string | null
  /** 抓取来源站点（审计） */
  scrapedSource?: string | null
  /** 站点特有元数据兜底 */
  extra?: Record<string, unknown>
  createdAt?: string | null
  updatedAt?: string | null
  tags?: Tag[]
  basicData?: Record<string, unknown>
  category?: string
}

/** 资源关联的物理文件（一个资源可含多文件） */
export interface ResourceFile {
  id?: number
  resourceId: number
  path: string
  /** 文件哈希，图片元数据匹配键 */
  sha256?: string | null
  size?: number | null
  format?: string | null
  /** 视频时长（秒） */
  duration?: number | null
  width?: number | null
  height?: number | null
  /** 视频编码 */
  codec?: string | null
  /** 图片拍摄时间（EXIF） */
  exifTakenAt?: string | null
  createdAt?: string | null
}

/** 标签 */
export interface Tag {
  id?: number
  name: string
}

/** 资源列表查询 */
export interface ResourcePageQuery {
  type?: ResourceType
  status?: ResourceStatus
  limit?: number
  offset?: number
  sort?: 'createdAt'
  order?: 'asc' | 'desc'
}

/** 资源列表分页信封 */
export interface ResourcePage {
  items: Resource[]
  total: number
  limit: number
  offset: number
  hasMore: boolean
}
