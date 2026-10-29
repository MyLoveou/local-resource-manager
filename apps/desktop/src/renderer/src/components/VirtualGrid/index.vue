<template>
  <div ref="scrollRef" class="virtual-grid">
    <div class="virtual-grid__spacer" :style="{ height: `${totalSize}px` }">
      <div v-for="vItem in virtualItems" :key="vItem.index" class="virtual-grid__cell" :data-index="vItem.index"
        :style="cellStyle(vItem)">
        <Card
          v-if="items[vItem.index]"
          :title="items[vItem.index].title"
          :cover-url="items[vItem.index].coverUrl"
          :badge="items[vItem.index].badge"
          :selected="items[vItem.index].selectable !== false && isSelected(items[vItem.index].id)"
          @click="handleCardClick($event, items[vItem.index].id)"
          @dblclick="handleCardDblClick($event, items[vItem.index].id)"
        />
      </div>
    </div>
    <div v-if="$slots.footer" class="virtual-grid__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useElementSize, useThrottleFn } from '@vueuse/core'
import { useVirtualizer, type VirtualItem } from '@tanstack/vue-virtual'
import { GRID_RESIZE_THROTTLE_MS } from '@/domain'
import Card from '../Card/index.vue'

export interface VirtualGridItem {
  id: number
  title: string
  coverUrl: string
  badge?: string
  /** 合集卡等不可选中项传 false */
  selectable?: boolean
}

const PADDING = 8

const props = withDefaults(
  defineProps<{
    items?: VirtualGridItem[]
    selectedIds?: number[]
    /** 单卡最小宽度，用于推算列数 */
    minItemWidth?: number
    gap?: number
    maxColumns?: number
  }>(),
  {
    items: () => [],
    selectedIds: () => [],
    minItemWidth: 160,
    gap: 8,
  }
)

const emit = defineEmits<{
  nearEnd: []
  cardClick: [MouseEvent, number]
  cardDblClick: [MouseEvent, number]
}>()
function handleCardClick(event: MouseEvent, itemId: number): void {
  emit('cardClick', event, itemId)
}

function handleCardDblClick(event: MouseEvent, itemId: number): void {
  emit('cardDblClick', event, itemId)
}

function isSelected(itemId: number): boolean {
  return props.selectedIds.includes(itemId)
}

const scrollRef = ref<HTMLElement | null>(null)
const { width } = useElementSize(scrollRef)
const layoutWidth = ref(0)
const applyLayoutWidth = useThrottleFn((next: number) => {
  layoutWidth.value = next
}, GRID_RESIZE_THROTTLE_MS)

watch(
  width,
  (next) => {
    if (layoutWidth.value <= 0) {
      layoutWidth.value = next
      return
    }
    applyLayoutWidth(next)
  },
  { immediate: true }
)

const items = computed(() => props.items ?? [])

const columns = computed(() => {
  const inner = layoutWidth.value - PADDING * 2
  if (inner <= 0) return 1
  const cols = Math.max(1, Math.floor((inner + props.gap) / (props.minItemWidth + props.gap)))
  return props.maxColumns ? Math.min(cols, props.maxColumns) : cols
})

const columnWidth = computed(() => {
  const inner = Math.max(0, layoutWidth.value - PADDING * 2)
  const cols = columns.value
  return (inner - props.gap * (cols - 1)) / cols
})

/** 封面 3/4 + 标题区 + 边框，与 Card 结构对齐 */
function estimateCardHeight(colWidth: number): number {
  if (colWidth <= 0) return 220
  const coverH = colWidth * (4 / 3)
  const titleBlock = 8 + 13 * 1.4 + 8
  const border = 2
  return Math.ceil(coverH + titleBlock + border)
}

const virtualizer = useVirtualizer(
  computed(() => ({
    count: items.value.length,
    getScrollElement: () => scrollRef.value,
    estimateSize: () => estimateCardHeight(columnWidth.value),
    overscan: 4,
    lanes: columns.value,
    gap: props.gap,
    paddingStart: PADDING,
    paddingEnd: PADDING,
  }))
)

const virtualItems = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

function cellStyle(vItem: VirtualItem): Record<string, string> {
  const left = PADDING + vItem.lane * (columnWidth.value + props.gap)
  return {
    position: 'absolute',
    top: '0',
    left: `${left}px`,
    width: `${columnWidth.value}px`,
    height: `${vItem.size}px`,
    transform: `translateY(${vItem.start}px)`,
  }
}

/** 同一批 items.length 只通知一次，避免滚动帧连发 */
let lastEmittedLength = -1

function maybeEmitNearEnd(): void {
  const len = items.value.length
  if (len === 0) return
  const vis = virtualizer.value.getVirtualItems()
  const maxIdx = vis.length > 0 ? Math.max(...vis.map((v) => v.index)) : -1
  const threshold = columns.value * 2
  const near = maxIdx >= len - threshold
  const el = scrollRef.value
  const unfilled = Boolean(el && el.scrollHeight <= el.clientHeight + 1)
  if ((near || unfilled) && lastEmittedLength !== len) {
    lastEmittedLength = len
    emit('nearEnd')
  }
}

watch(items, () => {
  lastEmittedLength = -1
})

watch([virtualItems, items, layoutWidth], maybeEmitNearEnd, { flush: 'post' })
</script>

<style scoped lang="less">
.virtual-grid {
  height: 100%;
  overflow: auto;
  position: relative;
}

.virtual-grid__spacer {
  position: relative;
  width: 100%;
}

.virtual-grid__footer {
  padding: 12px 8px 20px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}
</style>
