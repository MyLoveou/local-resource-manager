<template>
  <section class="stage">
    <div class="stage__head">
      <strong>{{ title }}</strong>
      <span class="stage__muted">{{ total }} 项</span>
      <span v-if="selected" class="stage__muted">· 已选 {{ selected }}</span>
      <span v-if="searching" class="stage__muted">· 全局搜索</span>
    </div>

    <div class="stage__tags">
      <button
        v-for="tag in tags"
        :key="tag.key"
        type="button"
        :class="['stage__tag', { 'is-on': picked.has(tag.en), 'is-artist': tag.cat === 'artist' }]"
        :title="`${tag.en}${tag.zh ? ' · ' + tag.zh : ''}`"
        @click="$emit('toggle', tag)"
      >
        <span class="stage__tag-name">{{ tag.zh || tag.en }}</span>
        <em v-if="tag.count" class="stage__tag-count">{{ compact(tag.count) }}</em>
      </button>
      <p v-if="!tags.length" class="stage__muted">没有匹配的标签</p>
    </div>

    <footer v-if="remaining > 0" class="stage__more">
      <button type="button" class="stage__more-btn" @click="$emit('more')">
        加载更多（还有 {{ remaining }}）
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { compact } from '@/domain/prompts/format'

export interface StageTag {
  key: string
  en: string
  zh: string
  count: number
  cat: string
}

defineProps<{
  title: string
  total: number
  tags: StageTag[]
  picked: Set<string>
  selected: number
  searching: boolean
  remaining: number
}>()

defineEmits<{
  toggle: [tag: StageTag]
  more: []
}>()
</script>

<style scoped lang="less">
.stage {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
}

.stage__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--sm-color-border, #e5e7eb);
  font-size: 12.5px;
}

.stage__muted {
  font-size: 11.5px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.stage__tags {
  flex: 1;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
}

.stage__tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  border-radius: 8px;
  padding: 4px 9px;
  font-size: 12.5px;
  color: inherit;
  cursor: pointer;
}

.stage__tag:hover {
  border-color: var(--sm-color-primary, #2080f0);
}

.stage__tag.is-on {
  border-color: var(--sm-color-primary, #2080f0);
  background: color-mix(in srgb, var(--sm-color-primary, #2080f0) 9%, transparent);
  color: var(--sm-color-primary, #2080f0);
}

.stage__tag.is-artist .stage__tag-name::before {
  content: '@';
  opacity: 0.5;
  margin-right: 1px;
}

.stage__tag-name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage__tag-count {
  font-style: normal;
  font-size: 10.5px;
  opacity: 0.5;
}

.stage__more {
  padding: 6px 12px;
  border-top: 1px solid var(--sm-color-border, #e5e7eb);
  text-align: center;
}

.stage__more-btn {
  border: none;
  background: transparent;
  color: var(--sm-color-primary, #2080f0);
  font-size: 11.5px;
  cursor: pointer;
}
</style>
