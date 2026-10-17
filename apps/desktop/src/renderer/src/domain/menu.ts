import type { RouteRecordRaw } from 'vue-router'

/** 菜单项（UI 无关的领域结构，供布局组件消费） */
export interface MenuItem {
  key: string
  label: string
  icon?: string
  disabled?: boolean
  children?: MenuItem[]
}

/** 从路由表生成菜单项，支持多级 children；isHidden 为可选谓词，默认不过滤 */
export function menuFromRoutes(
  routes: RouteRecordRaw[],
  isHidden?: (key: string) => boolean,
): MenuItem[] {
  return routes
    .filter((r) => !(r.meta as { hideMenu?: boolean } | undefined)?.hideMenu)
    .filter((r) => !isHidden?.(r.path))
    .map((r) => ({
    key: r.path,
    label: (r.meta?.title as string) ?? String(r.name ?? r.path),
    icon: r.meta?.icon as string | undefined,
    children: r.children ? menuFromRoutes(r.children, isHidden) : undefined,
  }))
}
