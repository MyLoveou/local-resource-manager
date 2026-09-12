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

/** 除查看器外：只允许缩略图，禁止 coverPath / content 回退。 */
export function resolveCardImageUrl(resource: { thumbnailPath?: string | null }): string {
  return resolveLibraryMediaUrl(resource.thumbnailPath)
}
