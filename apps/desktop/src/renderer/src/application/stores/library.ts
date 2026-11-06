/**
 * 库数据失效总线。
 *
 * 写操作只声明「哪些查询受影响」，订阅方各自按 scope/type 重取：
 * - resources：资源列表；按 type 失效，未指定 type 的混合列表监听全部
 * - categories：分类树与计数；按 type
 * - collections / savedViews / home / tags：对应页面或侧栏
 * - watchRevision：监视目录导入的软刷新（保留列表位置）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ResourceType } from '@/domain'

export type LibraryInvalidation = {
  resources?: true | ResourceType[]
  categories?: true | ResourceType[]
  collections?: boolean
  savedViews?: boolean
  home?: boolean
  tags?: boolean
}

export const useLibraryStore = defineStore('library', () => {
  const resourcesAll = ref(0)
  const resourcesByType = ref<Partial<Record<ResourceType, number>>>({})
  const categoriesAll = ref(0)
  const categoriesByType = ref<Partial<Record<ResourceType, number>>>({})
  const collectionsRevision = ref(0)
  const savedViewsRevision = ref(0)
  const homeRevision = ref(0)
  const tagsRevision = ref(0)

  const watchRevision = ref(0)
  const watchType = ref<ResourceType | null>(null)

  function bumpMap(map: typeof resourcesByType, type: ResourceType): void {
    map.value = {
      ...map.value,
      [type]: (map.value[type] ?? 0) + 1,
    }
  }

  function bumpResources(scope: true | ResourceType[]): void {
    if (scope === true) {
      resourcesAll.value += 1
      return
    }
    for (const type of scope) bumpMap(resourcesByType, type)
  }

  function bumpCategories(scope: true | ResourceType[]): void {
    if (scope === true) {
      categoriesAll.value += 1
      return
    }
    for (const type of scope) bumpMap(categoriesByType, type)
  }

  function invalidate(scope: LibraryInvalidation): void {
    if (scope.resources) bumpResources(scope.resources)
    if (scope.categories) bumpCategories(scope.categories)
    if (scope.collections) collectionsRevision.value += 1
    if (scope.savedViews) savedViewsRevision.value += 1
    if (scope.home) homeRevision.value += 1
    if (scope.tags) tagsRevision.value += 1
  }

  function resourceRevision(type?: ResourceType): number {
    if (type === undefined) {
      return (
        resourcesAll.value +
        Object.values(resourcesByType.value).reduce((sum, value) => sum + value, 0)
      )
    }
    return resourcesAll.value + (resourcesByType.value[type] ?? 0)
  }

  function categoryRevision(type?: ResourceType): number {
    if (type === undefined) {
      return (
        categoriesAll.value +
        Object.values(categoriesByType.value).reduce((sum, value) => sum + value, 0)
      )
    }
    return categoriesAll.value + (categoriesByType.value[type] ?? 0)
  }

  /** 监视目录自动导入：列表软刷新（refreshTop），同时刷新分类计数/首页/标签。 */
  function watchBump(type: ResourceType): void {
    watchType.value = type
    watchRevision.value += 1
    bumpCategories([type])
    homeRevision.value += 1
    tagsRevision.value += 1
  }

  return {
    resourcesAll,
    resourcesByType,
    categoriesAll,
    categoriesByType,
    collectionsRevision,
    savedViewsRevision,
    homeRevision,
    tagsRevision,
    watchRevision,
    watchType,
    invalidate,
    resourceRevision,
    categoryRevision,
    watchBump,
  }
})
