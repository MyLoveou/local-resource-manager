<template>
  <div class="collection-detail">
    <div class="collection-detail__head">
      <h2 class="collection-detail__title">
        {{ collection?.title ?? '合集' }}
      </h2>
      <n-button
        size="small"
        :disabled="selectedId === null"
        @click="moveSelected('up')"
      >
        上移
      </n-button>
      <n-button
        size="small"
        :disabled="selectedId === null"
        @click="moveSelected('down')"
      >
        下移
      </n-button>
      <n-button
        size="small"
        type="error"
        ghost
        :disabled="selectedId === null"
        @click="removeSelected"
      >
        移出
      </n-button>
      <n-button
        size="small"
        :disabled="members.length === 0"
        :loading="exporting"
        @click="exportToFolder"
      >
        导出
      </n-button>
      <n-popconfirm
        positive-text="删除"
        negative-text="取消"
        @positive-click="removeCollection"
      >
        <template #trigger>
          <n-button size="small" type="error" ghost>
            删除合集
          </n-button>
        </template>
        删除合集不会删除资源本身，确定？
      </n-popconfirm>
      <n-button
        size="small"
        @click="goBack"
      >
        返回
      </n-button>
    </div>
    <div v-if="types.length > 1" class="collection-detail__types">
      <button
        v-for="item in typeTabs"
        :key="item.value"
        type="button"
        class="collection-detail__type"
        :class="{ 'collection-detail__type--active': activeType === item.value }"
        @click="activeType = item.value"
      >
        {{ item.label }}
      </button>
    </div>
    <div class="collection-detail__filters">
      <n-select
        v-if="activeType !== 'all'"
        v-model:value="categoryId"
        size="small"
        clearable
        filterable
        placeholder="按分类筛选"
        :options="categoryOptions"
        class="collection-detail__filter"
      />
      <n-select
        v-model:value="tagIds"
        size="small"
        multiple
        clearable
        filterable
        placeholder="按标签筛选（AND）"
        :options="tagOptions"
        class="collection-detail__filter-tags"
      />
      <span class="collection-detail__count">
        {{ filteredMembers.length }} / {{ members.length }}
      </span>
    </div>
    <div
      v-if="!members.length && !loading"
      class="collection-detail__empty"
    >
      合集还没有成员。在资源的右侧信息栏里「加入合集」。
    </div>
    <div
      v-else-if="!filteredMembers.length && !loading"
      class="collection-detail__empty"
    >
      没有匹配当前分类/标签的成员。
    </div>
    <VirtualGrid
      v-else
      class="collection-detail__grid"
      :items="gridItems"
      :selected-ids="selectedId !== null ? [selectedId] : []"
      @card-click="onCardClick"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NPopconfirm, NSelect } from 'naive-ui'
import { notify } from '@/application/notify'
import { getCategoryTree, getTags, resolveCardImageUrl } from '@/infrastructure/http'
import { openResource } from '@/infrastructure/consume/consumeResource'
import {
  collectionMembers,
  deleteCollection as deleteCollectionApi,
  exportCollection,
  getCollection,
  moveCollectionItem,
  removeCollectionItem,
} from '@/infrastructure/http/collections'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import type { CategoryNode, Collection, Resource, ResourceType } from '@/domain'
import { RESOURCE_TYPE_LABEL, flattenCategoryTree } from '@/domain'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'

const route = useRoute()
const router = useRouter()
const selection = useSelectionStore()
const library = useLibraryStore()
const collection = ref<Collection | null>(null)
const members = ref<Resource[]>([])
const loading = ref(false)
const selectedId = computed(() => selection.selectedId)
const activeType = ref<ResourceType | 'all'>('all')
const categoryId = ref<number | null>(null)
const tagIds = ref<number[]>([])
const categoryTree = ref<CategoryNode[]>([])
const tagOptions = ref<{ label: string; value: number }[]>([])

const types = computed(() =>
  [...new Set(members.value.map((item) => item.type))],
)
const typeTabs = computed(() => [
  { label: '全部', value: 'all' as const },
  ...types.value.map((type) => ({
    label: RESOURCE_TYPE_LABEL[type] ?? type,
    value: type,
  })),
])
const categoryOptions = computed(() =>
  flattenCategoryTree(categoryTree.value).map((category) => ({
    label: category.name,
    value: category.id,
  })),
)
const categoryFilterIds = computed(() => {
  if (categoryId.value === null) return null
  const byId = new Map(flattenCategoryTree(categoryTree.value).map((node) => [node.id, node]))
  const ids = new Set<number>()
  const walk = (id: number): void => {
    if (ids.has(id)) return
    ids.add(id)
    for (const node of byId.values()) {
      if (node.parentId === id) walk(node.id)
    }
  }
  walk(categoryId.value)
  return ids
})

const filteredMembers = computed(() =>
  members.value.filter((item) => {
    if (activeType.value !== 'all' && item.type !== activeType.value) return false
    if (
      categoryFilterIds.value !== null &&
      !(item.categories ?? []).some((category) => category.id !== undefined && categoryFilterIds.value?.has(category.id))
    ) {
      return false
    }
    if (tagIds.value.length > 0) {
      const ids = new Set(
        (item.tags ?? []).flatMap((tag) => (tag.id === undefined ? [] : [tag.id]))
      )
      if (!tagIds.value.every((id) => ids.has(id))) return false
    }
    return true
  })
)

const gridItems = computed(() =>
  filteredMembers.value.flatMap((item) =>
    item.id === undefined
      ? []
      : [{ id: item.id, title: item.title, coverUrl: resolveCardImageUrl(item) }],
  ),
)

async function load(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) return
  loading.value = true
  try {
    collection.value = await getCollection(id)
    members.value = await collectionMembers(id)
    if (types.value.length === 1) activeType.value = types.value[0]
    loading.value = false
  } catch (error) {
    loading.value = false
    notify.fromError(error, { context: '读取合集' })
  }
}

function playlistFor(type: ResourceType): number[] {
  return filteredMembers.value.flatMap((item) =>
    item.id !== undefined && item.type === type ? [item.id] : [],
  )
}

function onCardClick(_event: MouseEvent, itemId: number): void {
  const item = members.value.find((row) => row.id === itemId)
  if (!item) return
  if (selection.selectedId === itemId) {
    void openResource(item, { playlist: playlistFor(item.type) })
    return
  }
  selection.select(itemId)
}

async function removeSelected(): Promise<void> {
  const id = Number(route.params.id)
  const rid = selectedId.value
  if (!Number.isFinite(id) || rid === null) return
  try {
    await removeCollectionItem(id, rid)
    selection.clear()
    library.invalidate({ collections: true, resources: true, home: true })
  } catch (error) {
    notify.fromError(error, { context: '移出合集' })
  }
}

async function moveSelected(direction: 'up' | 'down'): Promise<void> {
  const id = Number(route.params.id)
  const rid = selectedId.value
  if (!Number.isFinite(id) || rid === null) return
  try {
    await moveCollectionItem(id, rid, direction)
    library.invalidate({ collections: true, home: true })
  } catch (error) {
    notify.fromError(error, { context: '调整顺序' })
  }
}

async function removeCollection(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) return
  try {
    await deleteCollectionApi(id)
    library.invalidate({ collections: true, resources: true, home: true })
    notify.toast.success('已删除合集')
    void router.push('/collections')
  } catch (error) {
    notify.fromError(error, { context: '删除合集' })
  }
}

function goBack(): void {
  void router.push('/collections')
}

const exporting = ref(false)

async function exportToFolder(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) return
  const dir = await window.electron?.selectDirectory()
  if (!dir) return
  exporting.value = true
  try {
    const result = await exportCollection(id, dir)
    if (result.skipped > 0) {
      notify.toast.warning(`已导出 ${result.exported} 个文件，跳过 ${result.skipped} 个（文件缺失）`)
    } else {
      notify.toast.success(`已导出 ${result.exported} 个文件`)
    }
  } catch (error) {
    notify.fromError(error, { context: '导出合集' })
  } finally {
    exporting.value = false
  }
}

async function loadCategories(): Promise<void> {
  categoryId.value = null
  if (activeType.value === 'all') {
    categoryTree.value = []
    return
  }
  try {
    categoryTree.value = await getCategoryTree(activeType.value)
  } catch (error) {
    notify.fromError(error, { context: '读取分类' })
  }
}

onMounted(() => {
  selection.clear()
  void load()
  void getTags().then((tags) => {
    tagOptions.value = tags.flatMap((tag) =>
      tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
    )
  })
})

watch(activeType, () => {
  void loadCategories()
  selection.clear()
})

watch([categoryId, tagIds], () => {
  selection.clear()
})

watch(
  () => [
    library.categoryRevision(
      activeType.value === 'all' ? undefined : activeType.value,
    ),
    library.tagsRevision,
  ],
  () => {
    void loadCategories()
    void getTags().then((tags) => {
      tagOptions.value = tags.flatMap((tag) =>
        tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
      )
    })
  }
)

watch(
  () => [library.collectionsRevision, library.resourceRevision()],
  () => {
    if (Number.isFinite(Number(route.params.id))) void load()
  }
)
</script>

<style scoped lang="less">
.collection-detail {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: var(--sm-space-3);
}

.collection-detail__head {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  flex-shrink: 0;
  margin-bottom: var(--sm-space-2);
}

.collection-detail__title {
  font-size: 16px;
  margin: 0 var(--sm-space-2) 0 0;
}

.collection-detail__grid {
  flex: 1;
  min-height: 0;
}

.collection-detail__types {
  display: flex;
  gap: 4px;
  padding: 6px 0;
}

.collection-detail__type {
  border: 0;
  background: transparent;
  color: var(--sm-color-text-muted);
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;

  &--active {
    color: var(--sm-color-text);
    font-weight: 600;
    border-bottom: 2px solid var(--sm-color-accent, #2563eb);
  }
}

.collection-detail__filters {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  flex-shrink: 0;
  margin-bottom: var(--sm-space-2);
}

.collection-detail__filter {
  width: 160px;
}

.collection-detail__filter-tags {
  width: 260px;
}

.collection-detail__count {
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.collection-detail__empty {
  color: var(--sm-color-text-muted);
  font-size: 13px;
  margin-top: var(--sm-space-3);
}
</style>
