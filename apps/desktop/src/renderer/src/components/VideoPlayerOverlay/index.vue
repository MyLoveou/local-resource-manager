<template>
  <div v-show="player.visible" class="video-player-overlay" role="dialog" aria-modal="true">
    <div class="video-player-overlay__stage">
      <VideoPlayerHost
        v-if="player.visible && videoSrc && resumeReady"
        :src="videoSrc"
        :start-position="startPosition"
        :tracks="tracks"
        :audio-tracks="audioTracks"
        @progress="onProgress"
      />
    </div>
    <div v-if="nowPlayingLabel" class="video-player-overlay__now">{{ nowPlayingLabel }}</div>
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
import { getSubtitles } from '@/infrastructure/http/seriesAssets'
import { getAudioTracks, type AudioTrack } from '@/infrastructure/http/audio'
import type { SubtitleTrack } from '@/domain/subtitle'
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

/** 正在播放哪一集：集号 + 标题 + 时长，或特典标题 */
const nowPlayingLabel = computed(() => {
  const row = current.value
  const fileId = player.currentFileId ?? activeFile.value?.id
  if (!row || fileId == null) return ''
  for (const season of row.seasons ?? []) {
    for (const episode of season.episodes ?? []) {
      if (episode.fileId !== fileId) continue
      const parts = [`第 ${episode.episodeNumber} 集`]
      if (episode.title) parts.push(episode.title)
      const dur = formatDuration(episode.duration)
      if (dur) parts.push(dur)
      return parts.join(' · ')
    }
  }
  const extra = (row.extras ?? []).find((item) => item.fileId === fileId)
  if (extra) {
    const dur = formatDuration(extra.duration)
    return dur ? `${extra.title || '特典'} · ${dur}` : extra.title || '特典'
  }
  return ''
})

function formatDuration(seconds?: number | null): string {
  if (!seconds || !Number.isFinite(seconds) || seconds <= 0) return ''
  const total = Math.round(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60
  const pad = (value: number) => String(value).padStart(2, '0')
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(rest)}` : `${minutes}:${pad(rest)}`
}
/** 当前文件的音轨；多于一条时播放器才显示切换入口 */
const audioTracks = ref<AudioTrack[]>([])

watch(
  () => [player.visible, player.currentId, activeFile.value?.id] as const,
  async ([visible, id, fileId]) => {
    audioTracks.value = []
    if (!visible || id == null || fileId == null) return
    try {
      const list = await getAudioTracks(id, fileId)
      if (player.visible && player.currentId === id && activeFile.value?.id === fileId) {
        audioTracks.value = list
      }
    } catch {
      audioTracks.value = []
    }
  },
  { immediate: true },
)

/** 当前资源的字幕轨；按集过滤，资源级（episodeId 为空）始终可用 */
const tracks = ref<SubtitleTrack[]>([])
const subtitleEpisodeId = computed(() => {
  const fileId = player.currentFileId ?? activeFile.value?.id
  if (fileId == null) return null
  for (const season of current.value?.seasons ?? []) {
    for (const episode of season.episodes ?? []) {
      if (episode.fileId === fileId) return episode.id ?? null
    }
  }
  return null
})

watch(
  () => [player.visible, player.currentId] as const,
  async ([visible, id]) => {
    tracks.value = []
    if (!visible || id == null) return
    try {
      const all = await getSubtitles(id)
      if (!player.visible || player.currentId !== id) return
      const episodeId = subtitleEpisodeId.value
      tracks.value = all.filter(
        (track) => track.episodeId == null || episodeId == null || track.episodeId === episodeId,
      )
    } catch {
      tracks.value = []
    }
  },
  { immediate: true },
)

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

.video-player-overlay__now {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgb(0 0 0 / 55%);
  color: #fff;
  font-size: 13px;
  pointer-events: none;
}
.video-player-overlay__close {
  position: absolute;
  z-index: 21;
  top: 12px;
  right: 12px;
}
</style>
