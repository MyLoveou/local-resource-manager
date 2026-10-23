<template>
  <div v-show="visible" class="image-viewer-overlay" role="dialog" aria-modal="true">
    <div class="image-viewer-overlay__stage">
      <ImageViewerHost
        v-if="visible && imageSrc"
        :src="imageSrc"
        :animated="animated"
        :format="format"
        @open-external="openExternal"
      />
      <p v-if="trashed" class="image-viewer-overlay__trash">回收站预览 · 文件仍在，彻底删除前可查看</p>
    </div>
    <n-button class="image-viewer-overlay__similar" size="small" @click="findSimilar">
      找相似
    </n-button>
    <n-button class="image-viewer-overlay__close" size="small" circle aria-label="关闭" @click="close">
      ×
    </n-button>
    <n-button class="image-viewer-overlay__prev" size="small" circle :disabled="!hasPrev"
      aria-label="{{ NextAndPre[resource.type].prev }}" @click="prev">
      ‹
    </n-button>
    <n-button class="image-viewer-overlay__next" size="small" circle :disabled="!hasNext"
      aria-label="{{ NextAndPre[resource.type].next }}" @click="() => void next()">
      ›
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { storeToRefs } from 'pinia'
import ImageViewerHost from '@/components/ImageViewerHost/index.vue'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { FILE_ROLE, type Resource } from '@/domain'
import { getResource, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { notify } from '@/application/notify'
import { openPrimaryDefault } from '@/infrastructure/shell/openLibraryFile'
import { isAnimatedImageFormat } from '@/utils/imageFormat'

const viewer = useImageViewerStore()
const router = useRouter()
const { visible, currentId, hasPrev, hasNext, playlistIds } = storeToRefs(viewer)
const { close, prev, next } = viewer
const current = ref<Resource | null>(null)

const imageSrc = computed(() =>
  currentId.value == null || !visible.value
    ? ''
    : resolveLibraryMediaUrl(`/library/resources/${currentId.value}/content`)
)
const format = computed(() => {
  const files = current.value?.files ?? []
  return (files.find((file) => file.role === FILE_ROLE.PRIMARY) ?? files[0])?.format ?? null
})
const animated = computed(() => isAnimatedImageFormat(format.value))
const trashed = computed(() => current.value?.status === 'trashed')

async function openExternal(): Promise<void> {
  const message = await openPrimaryDefault(current.value)
  if (message) notify.toast.error(message)
}

function findSimilar(): void {
  const id = currentId.value
  if (id == null) return
  close()
  void router.push({ path: '/ai', query: { tab: 'similar', resourceId: String(id) } })
}

function prefetchNeighbors(id: number): void {
  const ids = playlistIds.value
  const i = ids.indexOf(id)
  for (const n of [i - 1, i + 1]) {
    if (n < 0 || n >= ids.length) continue
    const img = new Image()
    img.src = resolveLibraryMediaUrl(`/library/resources/${ids[n]}/content`)
  }
}

watch(
  () => [visible.value, currentId.value, playlistIds.value] as const,
  ([open, id]) => {
    if (!open || id == null) {
      current.value = null
      return
    }
    prefetchNeighbors(id)
    void getResource(id).then((row) => {
      if (currentId.value === id) current.value = row
    }).catch(() => {
      if (currentId.value === id) current.value = null
    })
  }
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
    void next()
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

.image-viewer-overlay__similar {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 6;
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

.image-viewer-overlay__trash {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 16px;
  z-index: 6;
  margin: 0;
  text-align: center;
  color: #d1d5db;
  font-size: 12px;
  pointer-events: none;
}
</style>
