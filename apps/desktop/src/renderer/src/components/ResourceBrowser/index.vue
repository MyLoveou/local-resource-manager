<template>
  <div class="resource-browser">
    <BrowseControls
      v-if="!hideControls"
      :type="type"
      :status="status"
      :placeholder="searchPlaceholder"
    />
    <p
      v-if="batchMessage"
      class="resource-browser__hint"
    >
      {{ batchMessage }}
    </p>
    <div
      v-if="loading && items.length === 0"
      class="resource-browser__state"
    >
      加载中…
    </div>
    <div
      v-else-if="error && items.length === 0"
      class="resource-browser__state"
    >
      <p>加载失败</p>
      <button
        type="button"
        class="resource-browser__retry"
        @click="reset"
      >
        重试
      </button>
    </div>
    <EmptyGuide
      v-else-if="!loading && total === 0"
      :hint="resolvedEmptyHint"
    />
    <!-- 根据类型判断显示什么资源 --->
    <JustifiedMediaGrid
      v-else-if="useJustified"
      class="resource-browser__grid"
      :tiles="justifiedTiles"
      :selected-ids="gridSelectedIds"
      interactive="grid"
      @near-end="loadMore"
      @card-click="handleCardClick"
    />
    <VirtualGrid
      v-else
      class="resource-browser__grid"
      :items="gridItems"
      :selected-ids="gridSelectedIds"
      @near-end="loadMore"
      @card-click="handleCardClick"
    >
      <template #footer>
        <span v-if="loadingMore">加载中…</span>
        <button
          v-else-if="error && items.length > 0"
          type="button"
          class="resource-browser__retry"
          @click="loadMore"
        >
          加载失败，点击重试
        </button>
        <span v-else-if="!hasMore && total > 0">已加载全部 {{ total }} 项</span>
      </template>
    </VirtualGrid>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import JustifiedMediaGrid from '@/components/JustifiedMediaGrid/index.vue'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import BrowseControls from '@/components/BrowseControls/index.vue'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'
import { useViewOptionsStore } from '@/application/stores/viewOptions'
import { useResourcePage } from '@/hooks/useResourcePage'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { useShellBatchStore } from '@/application/stores/shellBatch'
import { getResources, resolveCardImageUrl } from '@/infrastructure/http'
import { consumeResource } from '@/infrastructure/consume/consumeResource'
import { storeToRefs } from 'pinia'
import { isCollectionCard, type PhotoTile, type ResourceStatus, type ResourceType } from '@/domain'
import type { ResourceBatchAction } from '@/infrastructure/http'
import { PlayerByConsume } from '@/infrastructure/consume/players'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { consumeKindOf, TYPE_PROFILES } from '@/domain'
const BATCH_LIMIT = 200

const props = defineProps<{
  type?: ResourceType
  status?: ResourceStatus
  emptyHint: string
  /** ???????????????????? */
  hideControls?: boolean
  takenDate?: string
  untimed?: boolean
  timelineVisible?: boolean
  timelineMedia?: boolean
  includeCollectedOverride?: boolean
  categoryIdOverride?: number | null
  tagIdsOverride?: number[]
}>()

const isTrash = computed(() => props.status === 'trashed')
const selection = useSelectionStore()
const library = useLibraryStore()
const shellBatch = useShellBatchStore()
const browse = useBrowseQueryStore()
const viewOptions = useViewOptionsStore()
const session = computed(() => browse.ensure(props.type, props.status))
const searchPlaceholder = computed(() => (props.type ? '在本类中搜索' : isTrash.value ? '在回收站中搜索' : '在结果中筛选'))
const resolvedEmptyHint = computed(() =>
  session.value.q.trim() || session.value.tagIds.length
    ? '无匹配 · 搜索范围：标题 / 作者 / 描述 / 分类 / 标签 / 文件名'
    : props.emptyHint
)
const { selectedIds, selectedId } = storeToRefs(selection)
const { batchMode, message: batchMessage, busy: batchBusy } = storeToRefs(shellBatch)
const { items, total, hasMore, loading, loadingMore, error, reset, loadMore } = useResourcePage({
  type: () => props.type,
  status: () => props.status ?? 'active',
  q: () => session.value.q,
  sort: () => session.value.sort,
  order: () => session.value.order,
  tagIds: () => props.tagIdsOverride ?? session.value.tagIds,
  categoryId: () =>
    props.categoryIdOverride !== undefined ? props.categoryIdOverride : session.value.categoryId,
  includeCollected: () =>
    props.includeCollectedOverride === true ? true : viewOptions.includeCollected,
  takenDate: () => props.takenDate,
  untimed: () => props.untimed ?? false,
  timelineVisible: () => (props.timelineVisible === true ? true : undefined),
  timelineMedia: () => props.timelineMedia ?? false,
})
const { batchResources } = useResourceHandle()
const imageViewer = useImageViewerStore()
const route = useRoute()
const router = useRouter()

function pagerFor(resourceType: ResourceType) {
  return {
    hasMore: () => hasMore.value,
    loadingMore: () => loadingMore.value,
    loadMore,
    imageIds: () => ids(resourceType),
  }
}

function typesForPager(): readonly ResourceType[] {
  return props.type ? [props.type] : TYPE_PROFILES.map((profile) => profile.type)
}

function bindPagers(): void {
  for (const type of typesForPager()) {
    const kind = consumeKindOf(type)
    if (kind) PlayerByConsume[kind].bindPager?.(pagerFor(type))
  }
}

function unbindPagers(): void {
  for (const type of typesForPager()) {
    const kind = consumeKindOf(type)
    if (kind) PlayerByConsume[kind].unbindPager?.()
  }
}

bindPagers()

const useJustified = computed(() => props.type === 'image' || props.timelineMedia === true)

const gridSelectedIds = computed(() => {
  if (batchMode.value) return selectedIds.value
  return selectedId.value === null ? [] : [selectedId.value]
})

function handleCardClick(_event: MouseEvent, itemId: number | undefined): void {
  if (itemId === undefined) return
  const item = items.value.find((row) => row.id === itemId)
  // 合集卡：点击进入成员页
  if (item && isCollectionCard(item)) {
    void router.push(`/collections/${item.id}`)
    return
  }
  if (batchMode.value) {
    selection.toggle(itemId)
    return
  }
  if (selection.selectedId === itemId) {
    if (!item) return
    void consumeResource(item, ids(item.type))
    return
  }
  selection.select(itemId)
}

watch(
  () => route.query.select,
  (raw) => {
    const id = Number(raw)
    if (!Number.isFinite(id) || id <= 0) return
    selection.select(id)
  },
  { immediate: true },
)

function ids(type: ResourceType): number[] {
  return items.value.flatMap((item) =>
    item.id !== undefined && !isCollectionCard(item) && item.type === type ? [item.id] : []
  )
}

async function runBatch(action: ResourceBatchAction, tagNames?: string[]): Promise<void> {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  const live = shellBatch.ticket()
  batchBusy.value = true
  batchMessage.value = ''
  try {
    const result = await batchResources(action, ids, tagNames)
    library.bump(null)
    if (!shellBatch.isLive(live)) return
    if (action === 'add_tags') {
      batchMessage.value = `已为 ${result.ok.length} 项添加标签`
      selection.clear()
    } else {
      shellBatch.exit()
      if (result.failed.length > 0) {
        batchMessage.value = `完成 ${result.ok.length} 项，失败 ${result.failed.length} 项`
      }
    }
  } catch (err) {
    if (!shellBatch.isLive(live)) return
    batchMessage.value = '批量操作失败'
    console.error(err)
  } finally {
    if (shellBatch.isLive(live)) batchBusy.value = false
  }
}

async function collectTrashedIds(): Promise<number[]> {
  const ids: number[] = []
  let afterCreatedAt: string | undefined
  let afterId: number | undefined
  for (; ;) {
    const page = await getResources({
      status: 'trashed',
      limit: BATCH_LIMIT,
      afterCreatedAt,
      afterId,
    })
    ids.push(...page.items.flatMap((item) => (item.id === undefined ? [] : [item.id])))
    if (!page.hasMore || page.items.length === 0) break
    afterCreatedAt = page.nextCreatedAt ?? page.items[page.items.length - 1]?.createdAt ?? undefined
    afterId = page.nextId ?? page.items[page.items.length - 1]?.id
    if (afterId === undefined) break
  }
  return ids
}

async function emptyTrash(): Promise<void> {
  const live = shellBatch.ticket()
  batchBusy.value = true
  batchMessage.value = ''
  try {
    const ids = await collectTrashedIds()
    let failed = 0
    for (let i = 0; i < ids.length; i += BATCH_LIMIT) {
      const chunk = ids.slice(i, i + BATCH_LIMIT)
      const result = await batchResources('purge', chunk)
      failed += result.failed.length
    }
    library.bump(null)
    if (!shellBatch.isLive(live)) return
    shellBatch.exit()
    if (failed > 0) {
      batchMessage.value = `清空时有 ${failed} 项失败`
    }
  } catch (err) {
    if (!shellBatch.isLive(live)) return
    batchMessage.value = '清空回收站失败'
    console.error(err)
  } finally {
    if (shellBatch.isLive(live)) batchBusy.value = false
  }
}

watch(
  [isTrash, total],
  () => {
    shellBatch.bind({
      context: isTrash.value ? 'trash' : 'browse',
      emptyTrash,
      runBatch,
    })
    shellBatch.setTotal(total.value)
  },
  { immediate: true }
)

watch(
  () => props.type,
  (next, prev) => {
    if (prev != null && prev !== next) {
      const kind = consumeKindOf(prev)
      if (kind) PlayerByConsume[kind].close()
      shellBatch.exit()
    }
  }
)

watch(
  () => [hasMore.value, loadingMore.value] as const,
  () => {
    imageViewer.notifyPager()
  }
)

watch(
  () => library.revision,
  () => {
    if (imageViewer.visible) imageViewer.close()
  }
)

watch(
  () => [imageViewer.visible, imageViewer.currentId, items.value, hasMore.value] as const,
  () => {
    if (!imageViewer.visible) return
    const imageIds = ids('image')
    imageViewer.syncPlaylist(imageIds)
    const current = imageViewer.currentId
    if (current == null) return
    if (!imageIds.includes(current)) {
      imageViewer.close()
      return
    }
    const pos = imageIds.indexOf(current)
    if (pos >= imageIds.length - 2 && hasMore.value) {
      void loadMore()
    }
  }
)

onUnmounted(() => {
  unbindPagers()
  if (imageViewer.visible) imageViewer.close()
  shellBatch.unbind()
  const kind = props.type ? consumeKindOf(props.type) : undefined
  if (kind) PlayerByConsume[kind].close()
})

const justifiedTiles = computed<PhotoTile[]>(() =>
  items.value.flatMap((item) => {
    if (item.id === undefined || isCollectionCard(item)) return []
    const primary = item.files?.find((file) => file.role === 'primary')
    return [
      {
        id: item.id,
        title: item.title,
        kind: item.type === 'video' ? 'video' : 'image',
        width: primary?.width ?? null,
        height: primary?.height ?? null,
        duration: primary?.duration ?? null,
        thumbnailPath: item.thumbnailPath ?? null,
        takenAt: primary?.exifTakenAt ?? null,
      },
    ]
  })
)

const gridItems = computed(() =>
  items.value.flatMap((item) => {
    if (item.id === undefined) return []
    if (isCollectionCard(item)) {
      return [
        {
          id: item.id,
          title: item.title,
          coverUrl: resolveCardImageUrl(item),
          badge: `合集 · ${item.memberCount}`,
          selectable: false,
        },
      ]
    }
    return [
      {
        id: item.id,
        title: item.title,
        coverUrl: resolveCardImageUrl(item),
        badge: item.scrapePending ? '候选' : undefined,
      },
    ]
  })
)
</script>

<style scoped lang="less">
.resource-browser {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.resource-browser__hint {
  margin: var(--sm-space-1) var(--sm-space-2) 0;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.resource-browser__grid {
  flex: 1;
  min-height: 0;
}

.resource-browser__state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sm-space-3);
  height: 100%;
  color: var(--sm-color-text-muted);
}

.resource-browser__retry {
  border: 1px solid var(--sm-color-border);
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  padding: 6px var(--sm-space-3);
  border-radius: var(--sm-radius-control);
  cursor: pointer;
}
</style>
