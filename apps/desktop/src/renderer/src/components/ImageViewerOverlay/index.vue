<template>
  <div v-show="visible" class="image-viewer-overlay" role="dialog" aria-modal="true">
    <div class="image-viewer-overlay__stage">
      <ImageViewerHost v-if="visible && imageSrc" :src="imageSrc" />
    </div>
    <n-button
      class="image-viewer-overlay__close"
      size="small"
      circle
      aria-label="关闭"
      @click="close"
    >
      ×
    </n-button>
    <n-button
      class="image-viewer-overlay__prev"
      size="small"
      circle
      :disabled="!hasPrev"
      aria-label="上一张"
      @click="prev"
    >
      ‹
    </n-button>
    <n-button
      class="image-viewer-overlay__next"
      size="small"
      circle
      :disabled="!hasNext"
      aria-label="下一张"
      @click="next"
    >
      ›
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { NButton } from 'naive-ui'
import { storeToRefs } from 'pinia'
import ImageViewerHost from '@/components/ImageViewerHost/index.vue'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'

const viewer = useImageViewerStore()
const { visible, currentId, hasPrev, hasNext } = storeToRefs(viewer)
const { close, prev, next } = viewer

const imageSrc = computed(() =>
  currentId.value == null ? '' : resolveLibraryMediaUrl(`/library/resources/${currentId.value}/content`)
)

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(
    target.closest(
      'input, textarea, [contenteditable="true"], .n-input, .n-base-selection, .n-select, .n-rate'
    )
  )
}

function onKey(event: KeyboardEvent): void {
  if (!visible.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    if (document.fullscreenElement) {
      void document.exitFullscreen()
      return
    }
    close()
    return
  }
  if (isTypingTarget(event.target)) return
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    prev()
    return
  }
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    next()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<style scoped lang="less">
.image-viewer-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  background: #111;
}

.image-viewer-overlay__stage {
  position: absolute;
  inset: 0;

  :deep(.image-viewer-host-wrap) {
    position: absolute;
    inset: 0;
  }
}

.image-viewer-overlay__close,
.image-viewer-overlay__prev,
.image-viewer-overlay__next {
  position: absolute;
  z-index: 6;
}

.image-viewer-overlay__close {
  top: 12px;
  right: 12px;
}

.image-viewer-overlay__prev {
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
}

.image-viewer-overlay__next {
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
}
</style>
