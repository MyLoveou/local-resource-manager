<template>
  <aside class="composer">
    <div class="composer__tabs">
      <button
        type="button"
        :class="['composer__tab', { 'is-active': tab === 'positive' }]"
        @click="$emit('update:tab', 'positive')"
      >
        正面 <em>{{ positiveCount }}</em>
      </button>
      <button
        type="button"
        :class="['composer__tab', { 'is-active': tab === 'negative' }]"
        @click="$emit('update:tab', 'negative')"
      >
        负面 <em>{{ negativeCount }}</em>
      </button>
      <button v-if="tab === 'negative'" type="button" class="composer__link" @click="$emit('fill-negative')">
        载入模型负面
      </button>
    </div>

    <div class="composer__chips">
      <span v-for="(item, index) in items" :key="item.en" class="composer__chip">
        <span class="composer__chip-name" :title="item.en">{{ item.zh || item.en }}</span>
        <template v-if="tab === 'positive'">
          <button type="button" @click="$emit('bump', index, -0.1)">−</button>
          <em>{{ item.weight.toFixed(1) }}</em>
          <button type="button" @click="$emit('bump', index, 0.1)">+</button>
        </template>
        <button type="button" class="composer__x" @click="$emit('remove', index)">×</button>
      </span>
      <p v-if="!items.length" class="composer__muted">
        {{ tab === 'positive' ? '从中间点选标签' : '可留空，或载入模型负面' }}
      </p>
    </div>

    <textarea
      class="composer__out"
      rows="6"
      :readonly="tab === 'positive'"
      :value="output"
      @input="$emit('write', ($event.target as HTMLTextAreaElement).value)"
    />

    <div class="composer__head">
      <strong>最近存档</strong>
      <button type="button" class="composer__link" @click="$emit('refresh-saves')">刷新</button>
    </div>
    <ul v-if="saves.length" class="composer__saves">
      <li v-for="item in saves" :key="item.id">
        <img v-if="item.image_data" class="composer__thumb" :src="item.image_data" alt="" />
        <span v-else class="composer__thumb composer__thumb--empty" />
        <button type="button" class="composer__save-name" :title="item.positive" @click="$emit('load-save', item)">
          {{ item.title }}
        </button>
        <button type="button" class="composer__x" @click="$emit('remove-save', item.id)">×</button>
      </li>
    </ul>
    <p v-else class="composer__muted">还没有存档</p>
  </aside>
</template>

<script setup lang="ts">
import type { PromptSave } from '@/infrastructure/http/prompts'

export interface ComposerTag {
  en: string
  zh: string
  weight: number
}

defineProps<{
  tab: 'positive' | 'negative'
  items: ComposerTag[]
  output: string
  positiveCount: number
  negativeCount: number
  saves: PromptSave[]
}>()

defineEmits<{
  'update:tab': [value: 'positive' | 'negative']
  bump: [index: number, delta: number]
  remove: [index: number]
  'fill-negative': []
  write: [text: string]
  'refresh-saves': []
  'load-save': [item: PromptSave]
  'remove-save': [id: number]
}>()
</script>

<style scoped lang="less">
.composer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 12px;
  padding: 10px 12px;
  overflow: auto;
}

.composer__tabs {
  display: flex;
  align-items: center;
  gap: 6px;
}

.composer__tab {
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  border-radius: 999px;
  padding: 3px 12px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}

.composer__tab.is-active {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
}

.composer__tab em {
  font-style: normal;
  opacity: 0.65;
  margin-left: 2px;
}

.composer__link {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--sm-color-primary, #2080f0);
  font-size: 11.5px;
  cursor: pointer;
  padding: 0;
}

.composer__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 54px;
  max-height: 150px;
  overflow: auto;
  border: 1px dashed var(--sm-color-border, #e5e7eb);
  border-radius: 8px;
  padding: 8px;
}

.composer__chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 999px;
  padding: 2px 6px 2px 9px;
  font-size: 11.5px;
}

.composer__chip-name {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer__chip button {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
  opacity: 0.7;
}

.composer__chip em {
  font-style: normal;
  min-width: 22px;
  text-align: center;
  color: var(--sm-color-text-muted, #6b7280);
}

.composer__x {
  opacity: 0.45;
}

.composer__out {
  width: 100%;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 8px;
  padding: 8px;
  font-size: 12px;
  line-height: 1.55;
  font-family: inherit;
  resize: vertical;
  background: transparent;
  color: inherit;
}

.composer__head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
}

.composer__muted {
  margin: 0;
  font-size: 11.5px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.composer__saves {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.composer__saves li {
  display: flex;
  align-items: center;
  gap: 6px;
}

.composer__thumb {
  width: 24px;
  height: 24px;
  object-fit: cover;
  border-radius: 5px;
  flex-shrink: 0;
}

.composer__thumb--empty {
  background: var(--sm-color-bg-muted, #f3f4f6);
}

.composer__save-name {
  flex: 1;
  min-width: 0;
  text-align: left;
  border: none;
  background: transparent;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
  padding: 3px 4px;
  border-radius: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer__save-name:hover {
  background: var(--sm-color-bg-muted, #f3f4f6);
}
</style>
