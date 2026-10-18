<template>
  <div class="photo-row" :style="{ height: `${layout.containerHeight}px` }">
    <button
      v-for="(photo, index) in photos"
      :key="photo.id"
      type="button"
      class="photo-tile"
      :class="{ 'photo-tile--selected': photo.id === selectedId }"
      :style="boxStyle(layout.boxes[index])"
      :aria-label="photo.title || '照片'"
      @click="$emit('select', photo.id)"
      @dblclick="$emit('open', photo.id)"
    >
      <img
        v-if="photo.thumbnailPath"
        :src="resolveCardImageUrl({ thumbnailPath: photo.thumbnailPath, updatedAt: photo.takenAt })"
        :alt="photo.title || '照片'"
        class="photo-tile__img"
        loading="lazy"
        decoding="async"
        draggable="false"
      >
      <span v-else class="photo-tile__img photo-tile__img--empty">无缩略图</span>
      <span
        v-if="photo.kind === 'video' && photo.duration"
        class="photo-tile__duration"
      >{{ durationLabel(photo.duration) }}</span>
      <span class="photo-tile__overlay">
        <span v-if="photo.takenAt" class="photo-tile__time">{{ timeLabel(photo.takenAt) }}</span>
        <span class="photo-tile__title">{{ photo.title }}</span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { resolveCardImageUrl } from '@/infrastructure/http'
import type { PhotoTile } from '@/domain'

defineProps<{
  photos: PhotoTile[]
  layout: {
    containerHeight: number
    boxes: { left: number; top: number; width: number; height: number }[]
  }
  selectedId: number | null
}>()

defineEmits<{
  select: [id: number]
  open: [id: number]
}>()

function boxStyle(box: { left: number; top: number; width: number; height: number }): Record<string, string> {
  return {
    left: `${box.left}px`,
    top: `${box.top}px`,
    width: `${box.width}px`,
    height: `${box.height}px`,
  }
}

function timeLabel(takenAt: string): string {
  const time = takenAt.slice(11, 16)
  return time || ''
}

function durationLabel(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
}
</script>

<style scoped lang="less">
.photo-row {
  position: relative;
  width: 100%;
}

.photo-tile {
  position: absolute;
  overflow: hidden;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: var(--sm-color-bg-muted, #f1f1f1);
  cursor: pointer;
}

.photo-tile--selected {
  outline: 2px solid var(--sm-color-primary, #2563eb);
  outline-offset: -2px;
}

.photo-tile__img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-tile__img--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.photo-tile__overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 14px 8px 6px;
  color: #fff;
  font-size: 12px;
  text-align: left;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.55));
  opacity: 0;
  transition: opacity 0.15s ease;
}

.photo-tile:hover .photo-tile__overlay,
.photo-tile:focus-visible .photo-tile__overlay {
  opacity: 1;
}

.photo-tile__time {
  flex-shrink: 0;
  opacity: 0.9;
}

.photo-tile__duration {
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 11px;
}

.photo-tile__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
