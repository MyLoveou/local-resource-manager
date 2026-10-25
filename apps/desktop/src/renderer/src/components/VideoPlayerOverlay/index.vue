<template>
  <div v-show="player.visible" class="video-player-overlay" role="dialog" aria-modal="true">
    <div class="video-player-overlay__stage">
      <VideoPlayerHost
        v-if="player.visible && videoSrc && resumeReady"
        :src="videoSrc"
        :start-position="startPosition"
        @progress="onProgress"
      />
    </div>
    <n-button class="video-player-overlay__close" size="small" circle aria-label="关闭" @click="close">
      ×
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import VideoPlayerHost from '@/components/VideoPlayer/index.vue'
import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import {
  getPlaybackProgress,
  getResource,
  putPlaybackProgress,
  resolveLibraryMediaUrl,
} from '@/infrastructure/http'
import { PROGRESS_REPORT_INTERVAL_SECONDS } from '@/domain/progress'
import { FILE_ROLE, type Resource } from '@/domain'

const player = useVideoPlayerStore()
const current = ref<Resource | null>(null)
const startPosition = ref(0)
/** 续播位置取到之前不渲染播放器，避免先从头播再跳回去。 */
const resumeReady = ref(false)

let lastReported = 0
let lastSnapshot: { position: number; duration: number } | null = null

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

const activeFile = computed(() => {
  if (player.currentId == null || !player.visible) return undefined
  const files = current.value?.files ?? []
  const picked =
    player.currentFileId == null
      ? undefined
      : files.find((item) => item.id === player.currentFileId)
  return picked ?? files.find((item) => item.role === FILE_ROLE.PRIMARY) ?? files[0]
})

const videoSrc = computed(() => resolveLibraryMediaUrl(activeFile.value?.contentUrl ?? ''))

watch(
  () => [player.visible, player.currentId, activeFile.value?.id] as const,
  async ([visible, id, fileId]) => {
    startPosition.value = 0
    lastReported = 0
    lastSnapshot = null
    resumeReady.value = false
    if (!visible || id == null || fileId == null) return
    try {
      const saved = await getPlaybackProgress(id, fileId)
      if (!player.visible || player.currentId !== id || activeFile.value?.id !== fileId) return
      if (saved && !saved.completed && saved.position > 0) {
        startPosition.value = saved.position
        lastReported = saved.position
      }
    } catch {
      // 读不到续播位置不影响正常播放
    } finally {
      if (player.visible && player.currentId === id && activeFile.value?.id === fileId) {
        resumeReady.value = true
      }
    }
  },
  { immediate: true },
)

function onProgress(payload: { position: number; duration: number; ended: boolean }): void {
  lastSnapshot = { position: payload.position, duration: payload.duration }
  if (payload.ended) {
    void flush(true)
    return
  }
  if (payload.duration <= 0) return
  if (Math.abs(payload.position - lastReported) < PROGRESS_REPORT_INTERVAL_SECONDS) return
  void flush(false)
}

async function flush(ended: boolean): Promise<void> {
  const resourceId = player.currentId
  const fileId = activeFile.value?.id
  const snapshot = lastSnapshot
  if (resourceId == null || fileId == null || snapshot == null) return
  if (snapshot.duration <= 0 && !ended) return
  lastReported = snapshot.position
  try {
    await putPlaybackProgress(resourceId, {
      fileId,
      position: ended ? snapshot.duration : snapshot.position,
      duration: snapshot.duration > 0 ? snapshot.duration : null,
    })
  } catch {
    // 进度上报失败不打扰用户
  }
}

async function close(): Promise<void> {
  await flush(false)
  player.close()
}

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
  void close()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  void flush(false)
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
