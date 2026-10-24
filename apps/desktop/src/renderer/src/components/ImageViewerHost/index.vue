<template>
  <div class="image-viewer-host-wrap">
    <img
      v-if="animated"
      class="image-viewer-host__anim"
      :class="{ 'image-viewer-host__anim--hidden': loadError }"
      :src="src"
      alt=""
      draggable="false"
      :style="{ transform: `scale(${scale})` }"
      @wheel.prevent="onWheel"
      @error="onNativeError"
      @load="onNativeLoad"
    />
    <div
      v-else
      ref="hostRef"
      class="image-viewer-host"
      :class="{ 'image-viewer-host--hidden': loadError }"
    />
    <div v-if="loadError" class="image-viewer-host__error">
      <p>{{ errorText }}</p>
      <n-button size="small" @click="$emit('openExternal')">用外部应用打开</n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import {
  createInlineImageViewer,
  type InlineImageViewer,
} from '@/infrastructure/viewer/createInlineImageViewer'
import { isLikelyUnsupportedInlineFormat } from '@/utils/imageFormat'

const props = defineProps<{
  src: string
  animated?: boolean
  format?: string | null
}>()

defineEmits<{
  openExternal: []
}>()

const hostRef = ref<HTMLElement | null>(null)
const loadError = ref(false)
const scale = ref(1)
let viewer: InlineImageViewer | null = null
let resizeFrame = 0
let resizeTimer = 0
let observer: ResizeObserver | null = null

const errorText = computed(() =>
  isLikelyUnsupportedInlineFormat(props.format)
    ? '无法在应用内显示此图片（常见于 HEIC），请用系统看图软件打开。'
    : '无法显示此图片，请用系统应用打开。'
)

function destroyViewer(): void {
  observer?.disconnect()
  observer = null
  if (resizeFrame !== 0) {
    window.cancelAnimationFrame(resizeFrame)
    resizeFrame = 0
  }
  if (resizeTimer !== 0) {
    window.clearTimeout(resizeTimer)
    resizeTimer = 0
  }
  viewer?.destroy()
  viewer = null
}

function ensureViewer(): void {
  if (props.animated || viewer || !hostRef.value) return
  viewer = createInlineImageViewer(hostRef.value, {
    onError: () => {
      loadError.value = true
    },
    onLoad: () => {
      loadError.value = false
    },
  })
}

function scheduleResize(): void {
  if (resizeFrame !== 0) return
  resizeFrame = window.requestAnimationFrame(() => {
    resizeFrame = 0
    if (resizeTimer !== 0) window.clearTimeout(resizeTimer)
    resizeTimer = window.setTimeout(() => {
      resizeTimer = 0
      viewer?.resize()
    }, 80)
  })
}

function onNativeError(): void {
  loadError.value = true
}

function onNativeLoad(): void {
  loadError.value = false
}

function onWheel(event: WheelEvent): void {
  const next = event.deltaY < 0 ? scale.value * 1.1 : scale.value / 1.1
  scale.value = Math.min(8, Math.max(0.2, next))
}

onMounted(() => {
  if (props.animated) return
  ensureViewer()
  if (props.src) viewer?.setSrc(props.src)
  if (hostRef.value) {
    observer = new ResizeObserver(() => {
      scheduleResize()
    })
    observer.observe(hostRef.value)
  }
})

watch(
  () => [props.src, props.animated] as const,
  async ([url, animated]) => {
    loadError.value = false
    scale.value = 1
    if (animated) {
      destroyViewer()
      return
    }
    await nextTick()
    ensureViewer()
    if (url) viewer?.setSrc(url)
  }
)

onBeforeUnmount(() => {
  destroyViewer()
})
</script>

<style scoped lang="less">
.image-viewer-host-wrap {
  width: 100%;
  height: 100%;
  min-height: 0;
  position: relative;
}

.image-viewer-host {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #111;

  &--hidden {
    visibility: hidden;
  }

  :deep(.image-viewer-source) {
    position: absolute;
    left: 0;
    top: 0;
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    opacity: 0;
    pointer-events: none;
  }

  :deep(.viewer-container) {
    width: 100% !important;
    height: 100% !important;
    background: #111;
  }

  :deep(.viewer-canvas) {
    width: 100% !important;
    height: 100% !important;
  }

  :deep(.viewer-canvas > img) {
    max-width: none !important;
    max-height: none !important;
    margin: 0;
    object-fit: contain;
    will-change: transform;
  }

  :deep(.viewer-transition),
  :deep(.viewer-move) {
    transition: none !important;
  }
}

.image-viewer-host__anim {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transform-origin: center center;
  user-select: none;

  &--hidden {
    visibility: hidden;
  }
}

.image-viewer-host__error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  color: #e5e7eb;
  background: #111;
  text-align: center;
}
</style>
