<template>
  <div class="library-workspace">
    <TypeTabs :type="type" @change="changeType" />
    <div class="library-workspace__bar">
      <BrowseControls :type="type" placeholder="在资源库中搜索" />
    </div>
    <div class="library-workspace__body">
      <CategoryTreePanel
        :nodes="tree"
        :selected-id="session.categoryIds[0] ?? null"
        :uncategorized="session.uncategorized"
        @select="selectCategory"
        @manage="openManage"
        @create-child="openCreateChild"
      />
      <section class="library-workspace__content">
        <ResourceBrowser
          :key="`${type}-grid`"
          :type="type"
          :empty-hint="emptyHint"
          hide-controls
        />
      </section>
    </div>
    <CategoryManageModal
      v-model:show="manageOpen"
      :type="type"
      :nodes="tree"
      :initial-parent-id="manageParentId"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'
import { useCategoryTreeStore } from '@/application/stores/categoryTree'
import { useLibraryStore } from '@/application/stores/library'
import { profileFor, type ResourceType } from '@/domain'
import { isSectionHidden } from '@/domain/visibility'
import { notify } from '@/application/notify'
import TypeTabs from '@/components/LibraryWorkspace/TypeTabs.vue'
import CategoryTreePanel from '@/components/CategoryTreePanel/index.vue'
import CategoryManageModal from '@/components/CategoryManageModal/index.vue'
import BrowseControls from '@/components/BrowseControls/index.vue'
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'

const route = useRoute()
const router = useRouter()
const browse = useBrowseQueryStore()
const categoryStore = useCategoryTreeStore()
const library = useLibraryStore()
const manageOpen = ref(false)
const manageParentId = ref<number | null>(null)
let hydrating = false

const type = computed(() => route.params.type as ResourceType)
const session = computed(() => browse.ensure(type.value))
const tree = computed(() => categoryStore.treeFor(type.value))
const emptyHint = computed(() => profileFor(type.value)?.emptyHint ?? '暂无资源')

function parseIds(raw: unknown): number[] {
  if (Array.isArray(raw)) return raw.flatMap((item) => parseIds(item))
  if (typeof raw !== 'string' || !raw.trim()) return []
  return raw
    .split(',')
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item > 0)
}

function applyQuery(): void {
  const profile = profileFor(type.value)
  if (!profile || isSectionHidden(profile.routePath)) {
    void router.replace('/')
    return
  }
  const query = route.query
  hydrating = true
  browse.patch(type.value, undefined, {
    categoryIds: parseIds(query.categoryIds ?? query.categoryId),
    uncategorized: query.uncategorized === '1',
    tagIds: parseIds(query.tagIds),
    q: typeof query.q === 'string' ? query.q : '',
    sort: typeof query.sort === 'string' ? query.sort : session.value.sort,
    order: query.order === 'asc' ? 'asc' : 'desc',
    savedViewId: null,
  })
  hydrating = false
}

async function loadTree(): Promise<void> {
  try {
    await categoryStore.load(type.value)
  } catch (error) {
    notify.fromError(error, { context: '读取分类树' })
  }
}

function openManage(): void {
  manageParentId.value = null
  manageOpen.value = true
}

function openCreateChild(id: number): void {
  manageParentId.value = id
  manageOpen.value = true
}

function changeType(next: ResourceType): void {
  if (next === type.value) return
  browse.reset(next, undefined, true)
  void router.push({ path: `/library/${next}` })
}

function selectCategory(id: number | null, uncategorized: boolean): void {
  browse.patch(type.value, undefined, {
    categoryIds: id === null ? [] : [id],
    uncategorized,
    savedViewId: null,
  })
}

function syncQuery(): void {
  if (hydrating) return
  const current = session.value
  const query: Record<string, string> = {}
  if (current.categoryIds.length) query.categoryIds = current.categoryIds.join(',')
  if (current.uncategorized) query.uncategorized = '1'
  if (current.tagIds.length) query.tagIds = current.tagIds.join(',')
  if (current.q.trim()) query.q = current.q.trim()
  if (current.sort !== 'createdAt') query.sort = current.sort
  if (current.order !== 'desc') query.order = current.order
  const next = new URLSearchParams(query).toString()
  const path = next ? `/library/${type.value}?${next}` : `/library/${type.value}`
  if (route.fullPath.replace(/^#/, '') !== path) void router.replace(path)
}

watch(
  () => route.params.type,
  async () => {
    applyQuery()
    await loadTree()
  },
)

watch(
  () => library.categoryRevision(type.value),
  () => {
    void categoryStore.load(type.value, true)
  },
)

watch(session, syncQuery, { deep: true })

onMounted(async () => {
  applyQuery()
  await loadTree()
})
</script>

<style scoped lang="less">
.library-workspace {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.library-workspace__bar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 8px 12px;
  border-bottom: 1px solid var(--sm-color-border);
}

.library-workspace__bar :deep(.browse-controls) {
  flex: 1 1 100%;
  min-width: 0;
}

.library-workspace__body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.library-workspace__content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
