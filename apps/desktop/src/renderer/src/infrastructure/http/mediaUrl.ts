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

/** 除查看器外：只允许缩略图，禁止 coverPath / content 回退。 */
export function resolveCardImageUrl(resource: {
  thumbnailPath?: string | null
  updatedAt?: string | null
}): string {
  return withMediaCacheBust(resolveLibraryMediaUrl(resource.thumbnailPath), resource.updatedAt)
}
