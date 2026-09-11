/**
 * 把库内相对封面路径拼到当前后端地址。
 */
export function resolveLibraryMediaUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  const base = window.electron?.backend?.baseUrl ?? ''
  if (path.startsWith('/')) return `${base}${path}`
  return path
}
