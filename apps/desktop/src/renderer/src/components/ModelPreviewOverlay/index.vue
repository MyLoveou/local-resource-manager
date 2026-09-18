<template>
  <div v-show="preview.visible" class="model-preview-overlay" role="dialog" aria-modal="true">
    <model-viewer
      v-if="preview.visible && src"
      class="model-preview-overlay__stage"
      :src="src"
      camera-controls
    />
    <n-button class="model-preview-overlay__close" size="small" circle aria-label="关闭" @click="preview.close">
      ×
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { NButton } from 'naive-ui'
import '@google/model-viewer'
import { useModelPreviewStore } from '@/application/stores/modelPreview'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'

const preview = useModelPreviewStore()

const src = computed(() => {
  if (preview.resourceId == null || !preview.visible) return ''
  return resolveLibraryMediaUrl(`/library/resources/${preview.resourceId}/content`)
})

function onKey(event: KeyboardEvent): void {
  if (!preview.visible || event.key !== 'Escape') return
  event.preventDefault()
  preview.close()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped lang="less">
.model-preview-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  background: #111;
}

.model-preview-overlay__stage {
  width: 100%;
  height: 100%;
}

.model-preview-overlay__close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 21;
}
</style>
