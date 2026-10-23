import type { RouteRecordRaw } from 'vue-router'

/** 左侧导航项；group 只用于分组标题，不可点击。 */
export interface MenuItem {
  key: string
  label: string
  icon?: string
  disabled?: boolean
  type?: 'group'
  children?: MenuItem[]
}

const GROUP_ORDER = ['browse', 'view', 'organize', 'tools'] as const

const GROUP_LABELS: Record<(typeof GROUP_ORDER)[number], string> = {
  browse: '浏览',
  view: '视图',
  organize: '组织',
  tools: '工具',
}

type MenuRouteMeta = {
  hideMenu?: boolean
  menuGroup?: (typeof GROUP_ORDER)[number]
}

function groupForPath(path: string): (typeof GROUP_ORDER)[number] | null {
  if (path === '/' || path === '/library') return 'browse'
  if (path.startsWith('/timelines') || path.startsWith('/maps')) return 'view'
  if (
    path.startsWith('/collections') ||
    path.startsWith('/characters') ||
    path.startsWith('/persons')
  ) return 'organize'
  if (path === '/trash' || path === '/ai') return 'tools'
  return null
}

/** 从路由生成带分组的侧栏；没有明确分组或 hideMenu 的页面不进侧栏。 */
export function menuFromRoutes(
  routes: RouteRecordRaw[],
  isHidden?: (key: string) => boolean,
): MenuItem[] {
  const grouped = new Map<string, MenuItem[]>()

  for (const route of routes) {
    const meta = route.meta as MenuRouteMeta | undefined
    if (meta?.hideMenu || isHidden?.(route.path)) continue
    const group = meta?.menuGroup ?? groupForPath(route.path)
    if (!group) continue
    const items = grouped.get(group) ?? []
    items.push({
      key: route.path,
      label: (route.meta?.title as string) ?? String(route.name ?? route.path),
      icon: route.meta?.icon as string | undefined,
      children: route.children ? menuFromRoutes(route.children, isHidden) : undefined,
    })
    grouped.set(group, items)
  }

  return GROUP_ORDER.flatMap((group) => {
    const children = grouped.get(group)
    if (!children?.length) return []
    return [{
      key: `group-${group}`,
      label: GROUP_LABELS[group],
      type: 'group' as const,
      children,
    }]
  })
}
