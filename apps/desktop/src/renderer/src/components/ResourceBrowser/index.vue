<template>
  <div class="resource-browser-container">
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
    <InfoPanel :resource-id="activatedItemId" class="info-panel" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import { useResourcePage } from '@/hooks/useResourcePage'
import type { ResourceType } from '@/domain'
import InfoPanel from '@/ui/layouts/InfoPanel/index.vue'

const props = defineProps<{
  type: ResourceType
  emptyHint: string
}>()

const { items, total, hasMore, loading, loadingMore, error, reset, loadMore } = useResourcePage({
  type: props.type,
  status: 'active',
})

const activatedItemId = ref<number | undefined>(items.value[0]?.id)

function handleCardClick(itemId: number | undefined): void {
  if (itemId) {
    activatedItemId.value = itemId
  }
  console.log(activatedItemId.value)
}

const gridItems = computed(() =>
  items.value.map((item) => ({
    id: item.id,
    title: item.title,
    coverUrl: item.coverPath ?? '',
  }))
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

.resource-browser-container {
  display: flex;
  flex-direction: row;
  height: 100%;

  .resource-browser {
    flex: 1;
    height: 100%;
  }

  .info-panel {
    width: 350px;
    height: 100%;
  }
}
</style>
