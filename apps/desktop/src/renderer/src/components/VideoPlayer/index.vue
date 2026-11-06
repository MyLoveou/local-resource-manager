<template>
  <div class="video-player-host-wrap">
    <video
      v-if="src"
      ref="el"
      class="video-player-host"
      :src="sourceUrl"
      controls
      autoplay
      playsinline
      @loadedmetadata="seekToStart"
      @timeupdate="onTimeUpdate"
      @ratechange="onRateChange"
      @pause="emitProgress(false)"
      @ended="emitProgress(true)"
    >
      <track
        v-if="activeVttUrl"
        kind="subtitles"
        :src="activeVttUrl"
        srclang="zh"
        label="字幕"
        default
      />
    </video>
    <div class="video-player-subs">
      <select v-if="tracks.length" :value="activeId ?? ''" @change="onSelect">
        <option value="">字幕：关闭</option>
        <option v-for="track in tracks" :key="track.id" :value="track.id">
          {{ subtitleLabel(track) }}{{ track.renderable ? '' : '（渲染中…）' }}
        </option>
      </select>
      <select
        v-if="audioTracks.length > 1"
        :value="activeAudio ?? 0"
        title="音轨"
        @change="onAudioChange"
      >
        <option v-for="track in audioTracks" :key="track.index" :value="track.index">
          {{ track.label }}
        </option>
      </select>
      <span v-if="hint" class="video-player-subs__hint">{{ hint }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { destroyAssOverlay, mountAssOverlay } from '@/infrastructure/subtitles/assOverlay'
import { srtToVtt, subtitleLabel, type SubtitleTrack } from '@/domain/subtitle'
import type { AudioTrack } from '@/infrastructure/http/audio'

const props = withDefaults(
  defineProps<{
    src: string
    /** 续播起点（秒）。0 表示从头播放。 */
    startPosition?: number
    /** 可用字幕轨；空数组时不显示字幕入口。 */
    tracks?: SubtitleTrack[]
    /** 可用音轨；多于一条时显示切换。 */
    audioTracks?: AudioTrack[]
  }>(),
  { startPosition: 0, tracks: () => [], audioTracks: () => [] },
)

const emit = defineEmits<{
  progress: [payload: { position: number; duration: number; ended: boolean }]
}>()

const el = ref<HTMLVideoElement | null>(null)
const activeId = ref<number | null>(null)
const activeVttUrl = ref<string | null>(null)
const hint = ref('')

/** 播放速度交给原生控件（Chromium 自带倍速菜单），这里只负责记忆 */
const RATES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2] as const
const RATE_KEY = 'sm.player.rate'
const rate = ref<number>(loadRate())

function loadRate(): number {
  const raw = Number(localStorage.getItem(RATE_KEY))
  return RATES.includes(raw as (typeof RATES)[number]) ? raw : 1
}

function onRateChange(): void {
  const video = el.value
  if (!video) return
  rate.value = video.playbackRate
  localStorage.setItem(RATE_KEY, String(rate.value))
}

function applyRate(): void {
  const video = el.value
  if (video) video.playbackRate = rate.value
}

let objectUrl: string | null = null

/** 当前音轨：空 = 原文件默认音轨；切换时换成后端 remux 出来的单轨文件 */
const activeAudio = ref<number | null>(null)
const sourceUrl = computed(() => {
  const track = props.audioTracks.find((item) => item.index === activeAudio.value)
  return track ? track.url : props.src
})

/** 切音轨会换源，需要记住位置并在元数据就绪后跳回 */
let lastTime = 0
let restoreTo: number | null = null

function onTimeUpdate(): void {
  const video = el.value
  if (video) lastTime = video.currentTime
  emitProgress(false)
}

function onAudioChange(event: Event): void {
  const value = Number((event.target as HTMLSelectElement).value)
  restoreTo = lastTime
  activeAudio.value = Number.isFinite(value) ? value : null
}

/** 元数据就绪后再 seek，否则 currentTime 会被浏览器忽略。 */
function seekToStart(): void {
  const video = el.value
  if (!video) return
  applyRate()
  const target = restoreTo ?? props.startPosition ?? 0
  restoreTo = null
  if (target <= 0) return
  const duration = video.duration
  if (!Number.isFinite(duration) || target >= duration - 2) return
  video.currentTime = target
}

function emitProgress(ended: boolean): void {
  const video = el.value
  if (!video) return
  const duration = Number.isFinite(video.duration) ? video.duration : 0
  emit('progress', {
    position: ended && duration > 0 ? duration : video.currentTime,
    duration,
    ended,
  })
}

function clearVtt(): void {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
  activeVttUrl.value = null
}

async function onSelect(event: Event): Promise<void> {
  const raw = (event.target as HTMLSelectElement).value
  await activate(raw ? Number(raw) : null)
}

async function activate(id: number | null): Promise<void> {
  clearVtt()
  destroyAssOverlay()
  hint.value = ''
  activeId.value = id
  if (id === null) return

  const track = props.tracks.find((item) => item.id === id)
  const video = el.value
  if (!track || !video) return

  if (!track.renderable) {
    // ass/ssa：交给 libass-wasm 渲染，画在视频上方
    mountAssOverlay(video, track.url)
    hint.value = 'ass/ssa 由 libass 渲染，切换时可能短暂闪烁'
    return
  }

  try {
    const text = await fetch(track.url).then((res) => res.text())
    const vtt = track.format === 'vtt' ? text : srtToVtt(text)
    objectUrl = URL.createObjectURL(new Blob([vtt], { type: 'text/vtt' }))
    activeVttUrl.value = objectUrl
  } catch {
    hint.value = '字幕加载失败'
    activeId.value = null
  }
}

// 换片时回到「字幕关闭」与默认音轨，避免把上一条字幕/音轨带到新视频
watch(
  () => props.src,
  () => {
    activeAudio.value = null
    lastTime = 0
    restoreTo = null
    void activate(null)
  },
)

onBeforeUnmount(() => {
  clearVtt()
  destroyAssOverlay()
})
</script>

<style scoped lang="less">
.video-player-host-wrap {
  position: absolute;
  inset: 0;
  background: #111;
}

.video-player-host {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #111;
}

.video-player-subs {
  position: absolute;
  right: 12px;
  bottom: 64px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 6px;
  background: rgb(0 0 0 / 55%);
  color: #fff;
  font-size: 12px;
}

.video-player-subs__hint {
  opacity: 0.75;
}
</style>
