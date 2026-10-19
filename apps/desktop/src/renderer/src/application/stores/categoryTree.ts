import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { CategoryNode, ResourceType } from '@/domain'
import {
  createCategory,
  deleteCategory,
  getCategoryTree,
  invalidateCategoryTree,
  patchCategory,
} from '@/infrastructure/http'

export const useCategoryTreeStore = defineStore('categoryTree', () => {
  const trees = ref<Record<string, CategoryNode[]>>({})
  const loading = ref(false)
  const error = ref<unknown>(null)

  const treeFor = (type: ResourceType): CategoryNode[] => trees.value[type] ?? []
  const current = computed(() => treeFor)

  async function load(type: ResourceType, force = false): Promise<CategoryNode[]> {
    if (!force && trees.value[type]) return trees.value[type]
    loading.value = true
    error.value = null
    try {
      const tree = await getCategoryTree(type)
      trees.value = { ...trees.value, [type]: tree }
      return tree
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }

  function setTree(type: ResourceType, tree: CategoryNode[]): void {
    trees.value = { ...trees.value, [type]: tree }
  }

  async function create(
    type: ResourceType,
    body: { parentId?: number | null; name: string; sort?: number },
  ): Promise<CategoryNode[]> {
    const tree = await createCategory({ type, ...body })
    setTree(type, tree)
    return tree
  }

  async function update(
    id: number,
    type: ResourceType,
    body: { name?: string; parentId?: number | null; sort?: number },
  ): Promise<CategoryNode[]> {
    const tree = await patchCategory(id, type, body)
    setTree(type, tree)
    return tree
  }

  async function remove(id: number, type: ResourceType): Promise<void> {
    await deleteCategory(id, type)
    invalidateCategoryTree(type)
    delete trees.value[type]
  }

  function invalidate(type?: ResourceType): void {
    invalidateCategoryTree(type)
    if (type) delete trees.value[type]
    else trees.value = {}
  }

  return { trees, loading, error, current, treeFor, load, setTree, create, update, remove, invalidate }
})
