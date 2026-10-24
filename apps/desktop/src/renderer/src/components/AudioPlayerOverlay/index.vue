<template>
  <div v-show="player.visible" class="audio-player-overlay" role="dialog" aria-modal="true">
    <div class="audio-player-overlay__panel">
      <input class="audio-player-overlay__progress" type="range" min="0" max="1000" :value="progress" @input="onSeek" />
      <div class="audio-player-overlay__row">
        <n-button size="small" circle quaternary :disabled="!player.hasPrev" aria-label="上一首" @click="player.prev">
          <template #icon>
            <n-icon :size="20">
              <Icon icon="mdi:skip-previous" />
            </n-icon>
          </template>
        </n-button>
        <n-button size="small" circle quaternary :aria-label="playing ? '暂停' : '播放'" @click="togglePlay">
          <template #icon>
            <n-icon :size="20">
              <Icon :icon="playing ? 'mdi:pause' : 'mdi:play'" />
            </n-icon>
          </template>
        </n-button>
        <n-button size="small" circle quaternary :disabled="!player.hasNext" aria-label="下一首" @click="player.next">
          <template #icon>
            <n-icon :size="20">
              <Icon icon="mdi:skip-next" />
            </n-icon>
          </template>
        </n-button>
        <div class="audio-player-overlay__row-volume">
          <n-icon :size="18">
            <Icon icon="mdi:volume-high" />
          </n-icon>
          <input type="range" min="0" max="100" :value="volume" @input="onVolume" />
        </div>
      </div>
    </div>
    <n-button class="audio-player-overlay__close" size="small" circle aria-label="关闭" @click="close">
      <template #icon>
        <n-icon :size="16">
          <Icon icon="mdi:close" />
        </n-icon>
      </template>
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import { Icon } from '@iconify/vue'
import { Howl } from 'howler'
import { useAudioPlayerStore } from '@/application/stores/audioPlayer'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'

const player = useAudioPlayerStore()
const playing = ref(false)
const progress = ref(0)
const volume = ref(80)
let howl: Howl | null = null
let timer: number | null = null

const src = computed(() => {
  if (player.currentId == null || !player.visible) return ''
  return resolveLibraryMediaUrl(`/library/resources/${player.currentId}/content`)
})

function stopTimer(): void {
  if (timer != null) {
    window.clearInterval(timer)
    timer = null
  }
}

function unload(): void {
  stopTimer()
  howl?.unload()
  howl = null
  playing.value = false
  progress.value = 0
}

function load(): void {
  unload()
  if (!src.value) return
  howl = new Howl({
    src: [src.value],
    html5: true,
    volume: volume.value / 100,
    onend: () => {
      playing.value = false
    },
  })
  howl.play()
  playing.value = true
  timer = window.setInterval(() => {
    if (!howl) return
    const duration = howl.duration()
    if (duration > 0) progress.value = Math.round((howl.seek() as number / duration) * 1000)
  }, 250)
}

function togglePlay(): void {
  if (!howl) return
  if (howl.playing()) {
    howl.pause()
    playing.value = false
  } else {
    howl.play()
    playing.value = true
  }
}

function onSeek(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value)
  progress.value = value
  if (!howl) return
  const duration = howl.duration()
  if (duration > 0) howl.seek((value / 1000) * duration)
}

function onVolume(event: Event): void {
  volume.value = Number((event.target as HTMLInputElement).value)
  howl?.volume(volume.value / 100)
}

function close(): void {
  unload()
  player.close()
}

function onKey(event: KeyboardEvent): void {
  if (!player.visible || event.key !== 'Escape') return
  event.preventDefault()
  close()
}

watch(
  () => [player.visible, player.currentId] as const,
  ([visible]) => {
    if (visible) load()
    else unload()
  }
)

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  unload()
})
</script>

<style scoped lang="less">
.audio-player-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 17, 17, 0.72);
}

.audio-player-overlay__panel {
  width: min(480px, 90%);
  padding: 20px;
  border-radius: 8px;
  background: #1f2937;
  color: #f9fafb;
}

.audio-player-overlay__title {
  margin: 0 0 12px;
}

.audio-player-overlay__progress,
.audio-player-overlay__row input {
  width: 100%;
}

.audio-player-overlay__row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
}

.audio-player-overlay__row-volume {
  display: flex;
  flex: 1;
  min-width: 0;
  gap: 8px;
  align-items: center;
}

.audio-player-overlay__row :deep(.n-button) {
  color: #f9fafb;
}

.audio-player-overlay__close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 21;
}
</style>
