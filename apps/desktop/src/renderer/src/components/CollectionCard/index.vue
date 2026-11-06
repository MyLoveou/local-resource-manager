<template>
  <button type="button" class="collection-card" @click="$emit('open')">
    <span class="collection-card__stack">
      <span
        v-for="index in 3"
        :key="index"
        class="collection-card__layer"
        :class="`collection-card__layer--${index}`"
      >
        <img
          v-if="previews[index - 1]"
          :src="resolveLibraryMediaUrl(previews[index - 1])"
          alt=""
          loading="lazy"
        />
        <span v-else class="collection-card__placeholder" />
      </span>
    </span>
    <span class="collection-card__shade" />
    <span class="collection-card__title">{{ title }}</span>
    <span class="collection-card__count">{{ memberCount }} 项</span>
  </button>
</template>

<script setup lang="ts">
import { resolveLibraryMediaUrl } from '@/infrastructure/http'

defineProps<{
  title: string
  memberCount: number
  previews: string[]
}>()
defineEmits<{ open: [] }>()
</script>

<style scoped lang="less">
.collection-card {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  border: 0;
  border-radius: 12px;
  overflow: hidden;
  padding: 0;
  cursor: pointer;
  background: var(--sm-color-bg-muted, #f1f1f1);
  text-align: left;
  isolation: isolate;
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);

  &:focus-visible {
    outline: 2px solid var(--sm-color-accent, #2563eb);
    outline-offset: 2px;
  }

  &:hover {
    transform: translateY(-3px);
  }

  &:hover .collection-card__layer--2,
  &:focus-visible .collection-card__layer--2 {
    transform: translate(12%, 7%) rotate(7deg) scale(0.98);
  }

  &:hover .collection-card__layer--3,
  &:focus-visible .collection-card__layer--3 {
    transform: translate(22%, 12%) rotate(13deg) scale(0.95);
  }
}

.collection-card__stack {
  position: absolute;
  inset: 8%;
}

.collection-card__layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: 8px;
  background: var(--sm-color-bg-surface);
  box-shadow: 0 8px 18px rgb(0 0 0 / 18%);
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);

  &--1 {
    z-index: 3;
  }
  &--2 {
    z-index: 2;
    transform: translate(5%, 4%) rotate(3deg) scale(0.985);
  }
  &--3 {
    z-index: 1;
    transform: translate(10%, 8%) rotate(5deg) scale(0.97);
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.collection-card__placeholder {
  display: block;
  height: 100%;
  background: linear-gradient(135deg, #e5e7eb, #f9fafb);
}

.collection-card__shade {
  position: absolute;
  inset: 55% 0 0;
  background: linear-gradient(transparent, rgb(0 0 0 / 55%));
  z-index: 4;
}

.collection-card__title,
.collection-card__count {
  position: absolute;
  left: 12px;
  right: 12px;
  z-index: 5;
  color: #fff;
  text-shadow: 0 1px 4px rgb(0 0 0 / 40%);
}

.collection-card__title {
  bottom: 28px;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collection-card__count {
  bottom: 9px;
  font-size: 11px;
  opacity: 0.85;
}

@media (prefers-reduced-motion: reduce) {
  .collection-card__layer {
    transition: none;
  }
}
</style>
