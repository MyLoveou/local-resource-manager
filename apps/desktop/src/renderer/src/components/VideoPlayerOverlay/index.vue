<template>
  <div v-show="player.visible" class="video-player-overlay" role="dialog" aria-modal="true">
    <div class="video-player-overlay__stage">
      <VideoPlayerHost v-if="player.visible && videoSrc" :src="videoSrc" />
    </div>
    <n-button class="video-player-overlay__close" size="small" circle aria-label="关闭" @click="player.close">
      ×
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import VideoPlayerHost from '@/components/VideoPlayer/index.vue'
import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import { getResource, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { FILE_ROLE, type Resource } from '@/domain'

const player = useVideoPlayerStore()
const current = ref<Resource | null>(null)

watch(
  () => [player.visible, player.currentId] as const,
  async ([visible, id]) => {
    if (!visible || id == null) {
      current.value = null
      return
    }
    if (current.value?.id !== id) current.value = null
    try {
      const row = await getResource(id)
      if (player.visible && player.currentId === id) current.value = row
    } catch {
      if (player.currentId === id) current.value = null
    }
  },
  { immediate: true },
)

const videoSrc = computed(() => {
  if (player.currentId == null || !player.visible) return ''
  const files = current.value?.files ?? []
  const file = player.currentFileId == null
    ? undefined
    : files.find((item) => item.id === player.currentFileId)
  const primary = file ?? files.find((item) => item.role === FILE_ROLE.PRIMARY) ?? files[0]
  return resolveLibraryMediaUrl(primary?.contentUrl ?? '')
})

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(
    target.closest(
      'input, textarea, [contenteditable="true"], .n-input, .n-base-selection, .n-select, .n-rate'
    )
  )
}

function onKey(event: KeyboardEvent): void {
  if (!player.visible) return
  if (event.key !== 'Escape') return
  event.preventDefault()
  if (document.fullscreenElement) {
    void document.exitFullscreen()
    return
  }
  if (isTypingTarget(event.target)) return
  player.close()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<style scoped lang="less">
.video-player-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 20;
  display: flex;
  background: #111;
}

.video-player-overlay__stage {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.video-player-overlay__close {
  position: absolute;
  z-index: 21;
  top: 12px;
  right: 12px;
}
</style>
