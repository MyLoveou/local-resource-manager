<template>
  <div class="resource-browser">
    <div v-if="showToolbar" class="resource-browser__batch">
      <template v-if="!batchMode">
        <span v-if="isTrash">回收站 {{ total }} 项</span>
        <n-popconfirm
          v-if="isTrash"
          positive-text="清空"
          negative-text="取消"
          @positive-click="emptyTrash"
        >
          <template #trigger>
            <n-button size="tiny" type="error" ghost :disabled="batchBusy">清空回收站</n-button>
          </template>
          彻底删除回收站内全部条目，不可恢复。只删除库内副本，不删除你电脑上的原文件。
        </n-popconfirm>
        <n-button v-if="isTrash" size="tiny" :disabled="batchBusy" @click="enterBatchMode">
          批量选择
        </n-button>
        <n-button v-else size="tiny" :disabled="batchBusy" @click="enterBatchMode">批量删除</n-button>
      </template>
      <template v-else>
        <span>已选 {{ selectedCount }}</span>
        <template v-if="isTrash">
          <n-popconfirm
            positive-text="恢复"
            negative-text="取消"
            :disabled="selectedCount === 0"
            @positive-click="runBatch('restore')"
          >
            <template #trigger>
              <n-button size="tiny" :disabled="batchBusy || selectedCount === 0">恢复</n-button>
            </template>
            确定恢复所选资源？
          </n-popconfirm>
          <n-popconfirm
            positive-text="彻底删除"
            negative-text="取消"
            :disabled="selectedCount === 0"
            @positive-click="runBatch('purge')"
          >
            <template #trigger>
              <n-button size="tiny" type="error" ghost :disabled="batchBusy || selectedCount === 0">
                彻底删除
              </n-button>
            </template>
            彻底删除后不可恢复。只删除库内副本，不删除你电脑上的原文件。
          </n-popconfirm>
        </template>
        <n-popconfirm
          v-else
          positive-text="移入"
          negative-text="取消"
          :disabled="selectedCount === 0"
          @positive-click="runBatch('trash')"
        >
          <template #trigger>
            <n-button size="tiny" type="error" ghost :disabled="batchBusy || selectedCount === 0">
              移入回收站
            </n-button>
          </template>
          确定将所选资源移入回收站？可稍后恢复。
        </n-popconfirm>
        <n-button size="tiny" :disabled="batchBusy" @click="exitBatchMode">取消</n-button>
      </template>
    </div>
    <p v-if="batchMessage" class="resource-browser__hint">{{ batchMessage }}</p>
    <div v-if="loading && items.length === 0" class="resource-browser__state">加载中…</div>
    <div v-else-if="error && items.length === 0" class="resource-browser__state">
      <p>加载失败</p>
      <button type="button" class="resource-browser__retry" @click="reset">重试</button>
    </div>
    <EmptyGuide v-else-if="!loading && total === 0" :hint="emptyHint" />
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
        <button v-else-if="error && items.length > 0" type="button" class="resource-browser__retry" @click="loadMore">
          加载失败，点击重试
        </button>
        <span v-else-if="!hasMore && total > 0">已加载全部 {{ total }} 项</span>
      </template>
    </VirtualGrid>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { NButton, NPopconfirm } from 'naive-ui'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import { useResourcePage } from '@/hooks/useResourcePage'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { getResources, resolveCardImageUrl } from '@/infrastructure/http'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { storeToRefs } from 'pinia'
import type { ResourceStatus, ResourceType } from '@/domain'
import type { ResourceBatchAction } from '@/infrastructure/http'

const BATCH_LIMIT = 200

const props = defineProps<{
  type?: ResourceType
  status?: ResourceStatus
  emptyHint: string
}>()

const isTrash = computed(() => props.status === 'trashed')
const selection = useSelectionStore()
const library = useLibraryStore()
const imageViewer = useImageViewerStore()
const { selectedIds } = storeToRefs(selection)
const selectedCount = computed(() => selectedIds.value.length)
const { items, total, hasMore, loading, loadingMore, error, reset, loadMore } = useResourcePage({
  type: props.type,
  status: props.status ?? 'active',
})
const { batchResources } = useResourceHandle()
const batchBusy = ref(false)
const batchMessage = ref('')
const batchMode = ref(false)

const showToolbar = computed(() => total.value > 0 || batchMode.value)

/** 浏览模式不高亮多选框，只在批量模式画选中态 */
const gridSelectedIds = computed(() => (batchMode.value ? selectedIds.value : []))

function enterBatchMode(): void {
  batchMessage.value = ''
  selection.clear()
  batchMode.value = true
}

function exitBatchMode(): void {
  batchMode.value = false
  selection.clear()
}

function imageIds(): number[] {
  return items.value.flatMap((item) =>
    item.id !== undefined && item.type === 'image' ? [item.id] : []
  )
}

function handleCardClick(_event: MouseEvent, itemId: number | undefined): void {
  if (itemId === undefined) return
  if (batchMode.value) {
    selection.toggle(itemId)
    return
  }
  const item = items.value.find((row) => row.id === itemId)
  if (item?.type === 'image' && selection.selectedId === itemId) {
    imageViewer.open(itemId, imageIds())
    return
  }
  selection.select(itemId)
}

async function runBatch(action: ResourceBatchAction): Promise<void> {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  batchBusy.value = true
  batchMessage.value = ''
  try {
    const result = await batchResources(action, ids)
    library.bump(null)
    exitBatchMode()
    if (result.failed.length > 0) {
      batchMessage.value = `完成 ${result.ok.length} 项，失败 ${result.failed.length} 项`
    }
  } catch (err) {
    batchMessage.value = '批量操作失败'
    console.error(err)
  } finally {
    batchBusy.value = false
  }
}

async function collectTrashedIds(): Promise<number[]> {
  const ids: number[] = []
  let afterCreatedAt: string | undefined
  let afterId: number | undefined
  for (;;) {
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
    exitBatchMode()
    if (failed > 0) {
      batchMessage.value = `清空时有 ${failed} 项失败`
    }
  } catch (err) {
    batchMessage.value = '清空回收站失败'
    console.error(err)
  } finally {
    batchBusy.value = false
  }
}

onUnmounted(() => {
  exitBatchMode()
  imageViewer.close()
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

.resource-browser__batch {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 8px 8px 0;
  font-size: 13px;
  color: #374151;
}

.resource-browser__hint {
  margin: 4px 8px 0;
  font-size: 12px;
  color: #b45309;
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
  gap: 12px;
  height: 100%;
  color: #6b7280;
}

.resource-browser__retry {
  border: 1px solid #d1d5db;
  background: #fff;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}
</style>
