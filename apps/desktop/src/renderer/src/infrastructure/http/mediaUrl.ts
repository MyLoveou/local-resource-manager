/**
 * 把库内相对路径拼到当前后端地址。
 */
export function resolveLibraryMediaUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  const base = window.electron?.backend?.baseUrl ?? ''
  if (path.startsWith('/')) return `${base}${path}`
  return path
}

/** 缩略图 content URL 会被长缓存；用资源更新时间换查询串，避免换封面后仍画旧图。 */
export function withMediaCacheBust(url: string, revision?: string | null): string {
  if (!url || !revision) return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}v=${encodeURIComponent(revision)}`
}

/** 网格封面：优先缩略图，旧库/生成失败时回退到原封面或主文件。 */
export function resolveCardImageUrl(resource: {
  thumbnailPath?: string | null
  coverPath?: string | null
  updatedAt?: string | null
}): string {
  const path = resource.thumbnailPath || resource.coverPath || ''
  return withMediaCacheBust(resolveLibraryMediaUrl(path), resource.updatedAt)
}
