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
    <n-button
      class="image-viewer-overlay__slideshow"
      size="small"
      :disabled="!hasNext"
      :title="hasNext ? '每 3 秒切换到下一张' : '没有下一张图片'"
      @click="toggleSlideshow"
    >
      {{ slideshow ? '暂停' : '幻灯片' }}
    </n-button>
    <n-button
      class="image-viewer-overlay__compare-button"
      size="small"
      :disabled="!canCompare"
      @click="toggleCompare"
    >
      对比
    </n-button>
    <div v-if="compareOpen" class="image-viewer-overlay__compare">
      <div class="image-viewer-overlay__compare-head">
        <span>{{ current?.title || '当前图片' }} ↔ {{ compareSecond?.title || '选择对比图' }}</span>
        <div class="image-viewer-overlay__compare-actions">
          <n-select
            size="tiny"
            style="width: 150px"
            :options="compareOptions"
            :value="compareSecondId"
            @update:value="chooseCompareSecond"
          />
          <n-button size="tiny" @click="compareScale = Math.max(0.5, compareScale - 0.25)">−</n-button>
          <n-button size="tiny" @click="compareScale = 1">100%</n-button>
          <n-button size="tiny" @click="compareScale = Math.min(4, compareScale + 0.25)">+</n-button>
          <n-button size="tiny" @click="closeCompare">关闭</n-button>
        </div>
      </div>
      <div class="image-viewer-overlay__compare-grid" @wheel.prevent="onCompareWheel">
        <div class="image-viewer-overlay__compare-pane">
          <img :src="imageSrc" alt="" :style="{ transform: `scale(${compareScale})` }" />
        </div>
        <div class="image-viewer-overlay__compare-pane">
          <img v-if="compareSecondSrc" :src="compareSecondSrc" alt="" :style="{ transform: `scale(${compareScale})` }" />
        </div>
      </div>
    </div>
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
import { NButton, NSelect } from 'naive-ui'
import { storeToRefs } from 'pinia'
import ImageViewerHost from '@/components/ImageViewerHost/index.vue'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { FILE_ROLE, type Resource } from '@/domain'
import { getResource, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { notify } from '@/application/notify'
import { openPrimaryDefault } from '@/infrastructure/shell/openLibraryFile'
import {
  isAnimatedImageFormat,
  isLikelyUnsupportedInlineFormat,
  isWebpFormat,
  webpUrlIsAnimated,
} from '@/utils/imageFormat'

const viewer = useImageViewerStore()
const router = useRouter()
const { visible, currentId, hasPrev, hasNext, playlistIds } = storeToRefs(viewer)
const { close, prev, next } = viewer
const current = ref<Resource | null>(null)

const format = computed(() => {
  const files = current.value?.files ?? []
  return (files.find((file) => file.role === FILE_ROLE.PRIMARY) ?? files[0])?.format ?? null
})
const imageSrc = computed(() => {
  if (currentId.value == null || !visible.value) return ''
  const preview = current.value?.files?.find((file) => file.role === FILE_ROLE.PREVIEW)
  if (isLikelyUnsupportedInlineFormat(format.value) && preview?.id != null) {
    return resolveLibraryMediaUrl(
      `/library/resources/${currentId.value}/files/${preview.id}/content`,
    )
  }
  return resolveLibraryMediaUrl(`/library/resources/${currentId.value}/content`)
})
const animated = ref(false)
const slideshow = ref(false)
let slideshowTimer: ReturnType<typeof setInterval> | null = null
const compareOpen = ref(false)
const compareSecond = ref<Resource | null>(null)
const compareSecondId = ref<number | null>(null)
const compareScale = ref(1)
const compareOptions = computed(() =>
  playlistIds.value.map((id, index) => ({
    label: `第 ${index + 1} 张`,
    value: id,
  })),
)
const nextId = computed(() => {
  const index = currentId.value == null ? -1 : playlistIds.value.indexOf(currentId.value)
  return index >= 0 && index + 1 < playlistIds.value.length
    ? playlistIds.value[index + 1]
    : null
})
const canCompare = computed(() =>
  playlistIds.value.some((id) => id !== currentId.value),
)
const compareSecondSrc = computed(() => mediaSrcFor(compareSecond.value))
let animationCheck = 0
watch(
  [imageSrc, format],
  async ([url, value]) => {
    const check = ++animationCheck
    if (!url) {
      animated.value = false
      return
    }
    if (isAnimatedImageFormat(value) && !isWebpFormat(value)) {
      animated.value = true
      return
    }
    if (!isWebpFormat(value)) {
      animated.value = false
      return
    }
    animated.value = true
    const actual = await webpUrlIsAnimated(url)
    if (check === animationCheck && actual !== null) animated.value = actual
  },
  { immediate: true },
)
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

function stopSlideshow(): void {
  slideshow.value = false
  if (slideshowTimer !== null) {
    clearTimeout(slideshowTimer)
    slideshowTimer = null
  }
}

function scheduleSlideshow(): void {
  if (slideshowTimer !== null) {
    clearTimeout(slideshowTimer)
    slideshowTimer = null
  }
  if (!slideshow.value || !visible.value) return
  slideshowTimer = setTimeout(async () => {
    if (!slideshow.value || !visible.value) return
    if (!hasNext.value) {
      stopSlideshow()
      return
    }
    await next()
    if (slideshow.value && visible.value) scheduleSlideshow()
  }, 3000)
}

function toggleSlideshow(): void {
  if (slideshow.value) {
    stopSlideshow()
    return
  }
  if (!hasNext.value) {
    notify.toast.info('没有下一张图片')
    return
  }
  slideshow.value = true
  scheduleSlideshow()
}

function mediaSrcFor(row: Resource | null): string {
  if (row?.id == null) return ''
  const files = row.files ?? []
  const primary = files.find((file) => file.role === FILE_ROLE.PRIMARY) ?? files[0]
  const preview = files.find((file) => file.role === FILE_ROLE.PREVIEW)
  if (isLikelyUnsupportedInlineFormat(primary?.format) && preview?.id != null) {
    return resolveLibraryMediaUrl(
      `/library/resources/${row.id}/files/${preview.id}/content`,
    )
  }
  return resolveLibraryMediaUrl(`/library/resources/${row.id}/content`)
}

function closeCompare(): void {
  compareOpen.value = false
  compareSecond.value = null
  compareSecondId.value = null
  compareScale.value = 1
}

async function chooseCompareSecond(id: number): Promise<void> {
  if (id === currentId.value) return
  compareSecondId.value = id
  try {
    compareSecond.value = await getResource(id)
    compareScale.value = 1
  } catch {
    compareSecond.value = null
  }
}

async function toggleCompare(): Promise<void> {
  if (compareOpen.value) {
    closeCompare()
    return
  }
  const second = nextId.value ?? playlistIds.value.find((id) => id !== currentId.value)
  if (second == null) return
  stopSlideshow()
  compareOpen.value = true
  await chooseCompareSecond(second)
}

function onCompareWheel(event: WheelEvent): void {
  compareScale.value = Math.min(
    4,
    Math.max(0.5, compareScale.value + (event.deltaY < 0 ? 0.25 : -0.25)),
  )
}

watch(visible, (open) => {
  if (!open) {
    stopSlideshow()
    closeCompare()
  }
})

watch(currentId, () => {
  if (compareOpen.value) closeCompare()
})

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
    if (compareOpen.value) {
      closeCompare()
      return
    }
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
  stopSlideshow()
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

.image-viewer-overlay__similar,
.image-viewer-overlay__slideshow,
.image-viewer-overlay__compare-button,
.image-viewer-overlay__close,
.image-viewer-overlay__prev,
.image-viewer-overlay__next {
  --n-color: rgb(30 30 34 / 88%);
  --n-color-hover: rgb(50 50 56 / 96%);
  --n-color-pressed: rgb(70 70 76 / 96%);
  --n-text-color: #f5f5f5;
  --n-text-color-hover: #fff;
  --n-border: 1px solid rgb(255 255 255 / 28%);
  --n-border-hover: 1px solid rgb(255 255 255 / 55%);
  color: #f5f5f5;
  background: rgb(30 30 34 / 88%);
  border: 1px solid rgb(255 255 255 / 28%);
  box-shadow: 0 2px 10px rgb(0 0 0 / 35%);
}

.image-viewer-overlay__similar {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 6;
}

.image-viewer-overlay__slideshow {
  position: absolute;
  top: 12px;
  left: 88px;
  z-index: 6;
}

.image-viewer-overlay__compare-button {
  position: absolute;
  top: 12px;
  left: 154px;
  z-index: 6;
}

.image-viewer-overlay__compare {
  position: absolute;
  inset: 52px 12px 12px;
  z-index: 8;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border: 1px solid rgb(255 255 255 / 18%);
  border-radius: 8px;
  background: rgb(15 15 18 / 96%);
}

.image-viewer-overlay__compare-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #ddd;
  font-size: 12px;
}

.image-viewer-overlay__compare-actions {
  display: flex;
  gap: 4px;
}

.image-viewer-overlay__compare-grid {
  display: grid;
  flex: 1;
  min-height: 0;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.image-viewer-overlay__compare-pane {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 12%);
  border-radius: 6px;
  background: #050505;

  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transform-origin: center;
    transition: transform 80ms linear;
  }
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
