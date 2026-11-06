<template>
  <div ref="scrollRef" class="justified-media-grid" @scroll="onScroll">
    <PhotoRow
      v-if="tiles.length > 0"
      :photos="tiles"
      :layout="layout"
      :selected-ids="selectedIds"
      :interactive="interactive"
      @select="$emit('select', $event)"
      @open="$emit('open', $event)"
      @card-click="(event, id) => $emit('cardClick', event, id)"
    />
    <div v-if="tiles.length > 0" class="justified-media-grid__footer">
      <span v-if="loadingMore">加载中…</span>
      <button
        v-else-if="hasMore"
        type="button"
        class="justified-media-grid__more"
        @click="$emit('loadMore')"
      >
        加载更多
      </button>
      <span v-else>已加载全部 {{ total }} 项</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useElementSize } from '@vueuse/core'
import justifiedLayout from 'justified-layout'
import PhotoRow from '@/components/PhotoTimeline/PhotoRow.vue'
import type { PhotoTile } from '@/domain'

const props = withDefaults(
  defineProps<{
    tiles: PhotoTile[]
    selectedIds?: number[]
    interactive?: 'viewer' | 'grid'
    targetRowHeight?: number
    hasMore?: boolean
    loadingMore?: boolean
    total?: number
  }>(),
  {
    selectedIds: () => [],
    interactive: 'grid',
    targetRowHeight: 220,
    hasMore: true,
    loadingMore: false,
    total: 0,
  }
)

const emit = defineEmits<{
  nearEnd: []
  loadMore: []
  cardClick: [MouseEvent, number]
  select: [number]
  open: [number]
}>()

const scrollRef = ref<HTMLElement | null>(null)
const { width } = useElementSize(scrollRef)
const layoutWidth = computed(() => Math.max(1, width.value - 16))

const layout = computed(() => {
  if (props.tiles.length === 0) {
    return { containerHeight: 0, widowCount: 0, boxes: [] }
  }
  const ratios = props.tiles.map((tile) =>
    tile.width && tile.height ? tile.width / tile.height : 4 / 3
  )
  return justifiedLayout(ratios, {
    containerWidth: layoutWidth.value,
    targetRowHeight: props.targetRowHeight,
    boxSpacing: 6,
    containerPadding: 0,
  })
})

let lastEmittedLength = -1

function maybeEmitNearEnd(): void {
  const el = scrollRef.value
  if (!el || props.tiles.length === 0 || !props.hasMore) return
  const near = el.scrollTop + el.clientHeight >= el.scrollHeight - 600
  const unfilled = el.scrollHeight <= el.clientHeight + 1
  if ((near || unfilled) && lastEmittedLength !== props.tiles.length) {
    lastEmittedLength = props.tiles.length
    emit('nearEnd')
  }
}

function onScroll(): void {
  maybeEmitNearEnd()
}

watch(
  () => props.tiles.map((tile) => tile.id).join(','),
  async () => {
    lastEmittedLength = -1
    await nextTick()
    maybeEmitNearEnd()
  }
)

watch(width, async () => {
  await nextTick()
  maybeEmitNearEnd()
})

watch(
  () => props.hasMore,
  async () => {
    lastEmittedLength = -1
    await nextTick()
    maybeEmitNearEnd()
  }
)

onMounted(async () => {
  await nextTick()
  maybeEmitNearEnd()
})
</script>

<style scoped lang="less">
.justified-media-grid {
  height: 100%;
  overflow: auto;
  padding: 8px;
  box-sizing: border-box;
}

.justified-media-grid__footer {
  padding: 14px 8px 20px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.justified-media-grid__more {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: transparent;
  color: #374151;
  padding: 5px 14px;
  font-size: 13px;
  cursor: pointer;
}

.justified-media-grid__more:hover {
  border-color: #9ca3af;
  color: #111827;
}
</style>
