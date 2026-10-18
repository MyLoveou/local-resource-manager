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
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
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
  }>(),
  {
    selectedIds: () => [],
    interactive: 'grid',
    targetRowHeight: 220,
  }
)

const emit = defineEmits<{
  nearEnd: []
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
  if (!el || props.tiles.length === 0) return
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
  () => props.tiles.length,
  async () => {
    await nextTick()
    maybeEmitNearEnd()
  }
)
</script>

<style scoped lang="less">
.justified-media-grid {
  height: 100%;
  overflow: auto;
  padding: 8px;
  box-sizing: border-box;
}
</style>
