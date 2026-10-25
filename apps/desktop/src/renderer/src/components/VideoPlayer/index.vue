<template>
  <div class="video-player-host-wrap">
    <video
      v-if="src"
      ref="el"
      class="video-player-host"
      :src="src"
      controls
      autoplay
      playsinline
      @loadedmetadata="seekToStart"
      @timeupdate="emitProgress(false)"
      @pause="emitProgress(false)"
      @ended="emitProgress(true)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    src: string
    /** 续播起点（秒）。0 表示从头播放。 */
    startPosition?: number
  }>(),
  { startPosition: 0 },
)

const emit = defineEmits<{
  progress: [payload: { position: number; duration: number; ended: boolean }]
}>()

const el = ref<HTMLVideoElement | null>(null)

/** 元数据就绪后再 seek，否则 currentTime 会被浏览器忽略。 */
function seekToStart(): void {
  const video = el.value
  if (!video) return
  const target = props.startPosition ?? 0
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
</style>
