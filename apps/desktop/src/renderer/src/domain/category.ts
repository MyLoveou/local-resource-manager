import type { ResourceType } from './resource'

export interface CategoryNode {
  id: number
  type: ResourceType
  parentId?: number | null
  name: string
  sort: number
  isSystem: boolean
  count: number
  children?: CategoryNode[]
}

export function flattenCategoryTree(nodes: CategoryNode[]): CategoryNode[] {
  const out: CategoryNode[] = []
  const walk = (items: CategoryNode[]): void => {
    for (const item of items) {
      out.push(item)
      if (item.children?.length) walk(item.children)
    }
  }
  walk(nodes)
  return out
}

export function findCategory(nodes: CategoryNode[], id: number | null): CategoryNode | null {
  if (id === null) return null
  return flattenCategoryTree(nodes).find((node) => node.id === id) ?? null
}

export function categoryPath(nodes: CategoryNode[], id: number | null): CategoryNode[] {
  if (id === null) return []
  const byId = new Map(flattenCategoryTree(nodes).map((node) => [node.id, node]))
  const path: CategoryNode[] = []
  let current = byId.get(id)
  while (current) {
    path.unshift(current)
    current = current.parentId == null ? undefined : byId.get(current.parentId)
  }
  return path
}
