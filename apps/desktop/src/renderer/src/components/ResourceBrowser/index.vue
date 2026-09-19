<template>
  <div class="resource-browser">
    <BrowseControls :type="type" :status="status" :placeholder="searchPlaceholder" />
    <p v-if="batchMessage" class="resource-browser__hint">{{ batchMessage }}</p>
    <div v-if="loading && items.length === 0" class="resource-browser__state">加载中…</div>
    <div v-else-if="error && items.length === 0" class="resource-browser__state">
      <p>加载失败</p>
      <button type="button" class="resource-browser__retry" @click="reset">重试</button>
    </div>
    <EmptyGuide v-else-if="!loading && total === 0" :hint="resolvedEmptyHint" />
    <VirtualGrid v-else class="resource-browser__grid" :items="gridItems" :selected-ids="gridSelectedIds"
      @near-end="loadMore" @card-click="handleCardClick">
      <template #footer>
        <span v-if="loadingMore">加载中…</span>
        <button v-else-if="error && items.length > 0" type="button" class="resource-browser__retry" @click="loadMore">
          加载失败，点击重试
        </button>
        <span v-else-if="!hasMore && total > 0">已加载全部 {{ total }} 项</span>
      </template>
    </VirtualGrid>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import BrowseControls from '@/components/BrowseControls/index.vue'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'
import { useResourcePage } from '@/hooks/useResourcePage'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { useShellBatchStore } from '@/application/stores/shellBatch'
import { getResources, getResource, resolveCardImageUrl } from '@/infrastructure/http'
import { storeToRefs } from 'pinia'
import type { ResourceStatus, ResourceType } from '@/domain'
import type { ResourceBatchAction } from '@/infrastructure/http'
import { PlayerByConsume } from '@/static'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { consumeKindOf, FILE_ROLE, MODEL_PREVIEW_EXTENSIONS } from '@/domain'
import { openLaunchOrPrimary } from '@/infrastructure/shell/openLibraryFile'
const BATCH_LIMIT = 200

const props = defineProps<{
  type?: ResourceType
  status?: ResourceStatus
  emptyHint: string
}>()

const isTrash = computed(() => props.status === 'trashed')
const selection = useSelectionStore()
const library = useLibraryStore()
const shellBatch = useShellBatchStore()
const browse = useBrowseQueryStore()
const session = computed(() => browse.ensure(props.type, props.status))
const searchPlaceholder = computed(() => (props.type ? '在本类中搜索' : isTrash.value ? '在回收站中搜索' : '在结果中筛选'))
const resolvedEmptyHint = computed(() =>
  session.value.q.trim() || session.value.tagIds.length ? '无匹配' : props.emptyHint
)
const { selectedIds } = storeToRefs(selection)
const { batchMode, message: batchMessage, busy: batchBusy } = storeToRefs(shellBatch)
const { items, total, hasMore, loading, loadingMore, error, reset, loadMore } = useResourcePage({
  type: () => props.type,
  status: () => props.status ?? 'active',
  q: () => session.value.q,
  sort: () => session.value.sort,
  order: () => session.value.order,
  tagIds: () => session.value.tagIds,
})
const { batchResources } = useResourceHandle()
const imageViewer = useImageViewerStore()

imageViewer.bindPager({
  hasMore: () => hasMore.value,
  loadingMore: () => loadingMore.value,
  loadMore,
  imageIds: () => ids('image'),
})

const gridSelectedIds = computed(() => (batchMode.value ? selectedIds.value : []))

function handleCardClick(_event: MouseEvent, itemId: number | undefined): void {
  if (itemId === undefined) return
  if (batchMode.value) {
    selection.toggle(itemId)
    return
  }
  const item = items.value.find((row) => row.id === itemId)
  if (selection.selectedId === itemId) {
    if (!item) return
    const kind = consumeKindOf(item.type)
    if (kind == null || kind === 'overlay-series') return
    if (kind === 'shell-open') {
      void getResource(itemId).then((row) => openLaunchOrPrimary(row))
      return
    }
    if (kind === 'overlay-model') {
      void getResource(itemId).then((row) => {
        const format = (row.files?.find((file) => file.role === FILE_ROLE.PRIMARY)?.format ?? '').toLowerCase()
        if ((MODEL_PREVIEW_EXTENSIONS as readonly string[]).includes(format)) {
          PlayerByConsume[kind].open(itemId, ids(item.type))
          return
        }
        void openLaunchOrPrimary(row)
      })
      return
    }
    PlayerByConsume[kind].open(itemId, ids(item.type))
    return
  }
  selection.select(itemId)
}

function ids(type: ResourceType): number[] {
  return items.value.flatMap((item) =>
    item.id !== undefined && item.type === type ? [item.id] : []
  )
}

async function runBatch(action: ResourceBatchAction): Promise<void> {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  const live = shellBatch.ticket()
  batchBusy.value = true
  batchMessage.value = ''
  try {
    const result = await batchResources(action, ids)
    library.bump(null)
    if (!shellBatch.isLive(live)) return
    shellBatch.exit()
    if (result.failed.length > 0) {
      batchMessage.value = `完成 ${result.ok.length} 项，失败 ${result.failed.length} 项`
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
  imageViewer.unbindPager()
  if (imageViewer.visible) imageViewer.close()
  shellBatch.unbind()
  const kind = props.type ? consumeKindOf(props.type) : undefined
  if (kind) PlayerByConsume[kind].close()
})

const gridItems = computed(() =>
  items.value.flatMap((item) =>
    item.id === undefined
      ? []
      : [
        {
          id: item.id,
          title: item.title,
          coverUrl: resolveCardImageUrl(item),
        },
      ]
  )
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
