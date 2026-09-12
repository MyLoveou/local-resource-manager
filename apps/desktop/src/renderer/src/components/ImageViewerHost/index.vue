<template>
  <div class="image-viewer-host-wrap">
    <div ref="hostRef" class="image-viewer-host" :class="{ 'image-viewer-host--hidden': loadError }" />
    <div v-if="loadError" class="image-viewer-host__error">
      无法显示此图片，请用右侧「更多」里的「用外部应用打开」
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  createInlineImageViewer,
  type InlineImageViewer,
} from '@/infrastructure/viewer/createInlineImageViewer'

const props = defineProps<{
  src: string
}>()

const hostRef = ref<HTMLElement | null>(null)
const loadError = ref(false)
let viewer: InlineImageViewer | null = null
let resizeFrame = 0
let resizeTimer = 0
let observer: ResizeObserver | null = null

function ensureViewer(): void {
  if (viewer || !hostRef.value) return
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

onMounted(() => {
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
  () => props.src,
  (url) => {
    loadError.value = false
    ensureViewer()
    if (url) viewer?.setSrc(url)
  }
)

onBeforeUnmount(() => {
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

  /* Viewer 默认 canvas img 带 max-width:90%，会只压宽度、高度仍按脚本像素，造成拉伸 */
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

.image-viewer-host__error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #e5e7eb;
  background: #111;
  text-align: center;
}
</style>
