<template>
  <div class="resource-browser">
    <div v-if="loading && items.length === 0" class="resource-browser__state">加载中…</div>
    <div v-else-if="error && items.length === 0" class="resource-browser__state">
      <p>加载失败</p>
      <button type="button" class="resource-browser__retry" @click="reset">重试</button>
    </div>
    <EmptyGuide v-else-if="!loading && total === 0" :hint="emptyHint" />
    <VirtualGrid v-else :items="gridItems" @near-end="loadMore" @card-click="handleCardClick">
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
import { computed, onUnmounted } from 'vue'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import { useResourcePage } from '@/hooks/useResourcePage'
import { useSelectionStore } from '@/application/stores/selection'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'
import type { ResourceType } from '@/domain'

const props = defineProps<{
  type: ResourceType
  emptyHint: string
}>()

const selection = useSelectionStore()
const { items, total, hasMore, loading, loadingMore, error, reset, loadMore } = useResourcePage({
  type: props.type,
  status: 'active',
})

function handleCardClick(itemId: number | undefined): void {
  if (itemId !== undefined) {
    selection.select(itemId)
  }
}

onUnmounted(() => {
  selection.clear()
})

const gridItems = computed(() =>
  items.value.flatMap((item) =>
    item.id === undefined
      ? []
      : [
          {
            id: item.id,
            title: item.title,
            coverUrl: resolveLibraryMediaUrl(item.thumbnailPath ?? item.coverPath),
          },
        ]
  )
)
</script>

<style scoped lang="less">
.resource-browser {
  height: 100%;
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
