/**
 * 分区可见性（代码级配置）：改清单并重启即可隐藏分区入口。
 * 规则：命中菜单/路由/导入/首页；只影响入口，不改资源与 API。
 * 首页 `/` 不可隐藏；未知 path 忽略。
 */
export const HIDDEN_SECTIONS: readonly string[] = [
  '/av',
  '/anime',
  '/novel',
  '/comic',
  '/game',
  '/model',
]

/** 路由 path 是否属于隐藏分区（精确命中或子路径前缀）。 */
export function isSectionHidden(path: string): boolean {
  if (!path || path === '/') return false
  const candidate = path.startsWith('/library/')
    ? `/${path.split('/')[2] ?? ''}`
    : path
  return HIDDEN_SECTIONS.some((key) => {
    if (!key || key === '/') return false
    const section = key.endsWith('/') ? key.slice(0, -1) : key
    return candidate === section || candidate.startsWith(`${section}/`)
  })
}
