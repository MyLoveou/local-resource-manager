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
import { computed, onMounted, onUnmounted } from 'vue'
import { NButton } from 'naive-ui'
import VideoPlayerHost from '@/components/VideoPlayer/index.vue'
import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'

const player = useVideoPlayerStore()

const videoSrc = computed(() =>
  player.currentId == null || !player.visible
    ? ''
    : resolveLibraryMediaUrl(`/library/resources/${player.currentId}/content`)
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
