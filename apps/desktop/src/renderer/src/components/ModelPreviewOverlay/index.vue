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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import '@google/model-viewer'
import { useModelPreviewStore } from '@/application/stores/modelPreview'
import { getResource, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { FILE_ROLE, type Resource } from '@/domain'

const preview = useModelPreviewStore()
const current = ref<Resource | null>(null)

watch(
  () => [preview.visible, preview.resourceId] as const,
  async ([visible, id]) => {
    if (!visible || id == null) {
      current.value = null
      return
    }
    if (current.value?.id !== id) current.value = null
    try {
      const row = await getResource(id)
      if (preview.visible && preview.resourceId === id) current.value = row
    } catch {
      if (preview.resourceId === id) current.value = null
    }
  },
  { immediate: true },
)

const src = computed(() => {
  if (preview.resourceId == null || !preview.visible) return ''
  const files = current.value?.files ?? []
  const primary = files.find((file) => file.role === FILE_ROLE.PRIMARY) ?? files[0]
  return resolveLibraryMediaUrl(primary?.contentUrl ?? '')
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
