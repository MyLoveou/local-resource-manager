<template>
  <section class="info-panel-section">
    <div class="info-panel-section-title">组织</div>
    <div class="info-panel-label">评分</div>
    <n-rate
      allow-half
      :count="5"
      :value="rating"
      @update:value="emit('update:rating', $event)"
    />
    <div class="info-panel-label">分类</div>
    <n-select
      multiple
      filterable
      clearable
      :options="categoryOptions"
      :value="categoryIds"
      @update:value="(value: number[]) => emit('update:category-ids', value ?? [])"
    />
    <div class="info-panel-label">标签（Enter 添加）</div>
    <div class="info-panel-tags">
      <n-tag v-for="name in tagNames" :key="name" closable @close="emit('remove-tag', name)">
        {{ name }}
      </n-tag>
      <n-input
        :value="tagInput"
        placeholder="输入标签"
        size="small"
        style="width: 120px"
        @update:value="emit('update:tag-input', $event)"
        @keydown.enter.prevent="emit('commit-tag')"
      />
    </div>
    <div class="info-panel-label">角色</div>
    <n-select
      multiple
      filterable
      clearable
      :options="characterOptions"
      :value="characterIds"
      :loading="characterBusy"
      @update:value="(value: number[]) => emit('update:characters', value ?? [])"
    />
    <div class="info-panel-label">扮演者</div>
    <n-select
      multiple
      filterable
      clearable
      :options="personOptions"
      :value="personIds"
      :loading="personBusy"
      @update:value="(value: number[]) => emit('update:persons', value ?? [])"
    />
  </section>
</template>

<script setup lang="ts">
import { NInput, NRate, NSelect, NTag } from 'naive-ui'

defineProps<{
  rating: number
  categoryOptions: { label: string; value: number }[]
  categoryIds: number[]
  tagNames: string[]
  tagInput: string
  characterOptions: { label: string; value: number }[]
  characterIds: number[]
  characterBusy: boolean
  personOptions: { label: string; value: number }[]
  personIds: number[]
  personBusy: boolean
}>()

const emit = defineEmits<{
  'update:rating': [value: number]
  'update:category-ids': [value: number[]]
  'update:tag-input': [value: string]
  'remove-tag': [name: string]
  'commit-tag': []
  'update:characters': [value: number[]]
  'update:persons': [value: number[]]
}>()
</script>

<style scoped lang="less">
.info-panel-section {
  padding: 12px 0;
}

.info-panel-section-title {
  color: var(--sm-color-text);
  font-size: 12px;
  font-weight: 600;
}

.info-panel-label {
  margin: 12px 0 6px;
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.info-panel-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
