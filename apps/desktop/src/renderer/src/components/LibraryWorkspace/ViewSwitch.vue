<template>
  <div class="view-switch">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="view-switch__item"
      :class="{ 'view-switch__item--active': item.value === view }"
      :disabled="item.disabled"
      @click="$emit('change', item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { ViewMode } from '@/domain'

defineProps<{ view: ViewMode }>()
defineEmits<{ change: [view: ViewMode] }>()

const items: { label: string; value: ViewMode; disabled?: boolean }[] = [
  { label: '网格', value: 'grid' },
  { label: '地图', value: 'map' },
]
</script>

<style scoped lang="less">
.view-switch {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--sm-color-border);
  border-radius: 6px;
  overflow: hidden;
}

.view-switch__item {
  border: 0;
  background: transparent;
  color: var(--sm-color-text-muted);
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;

  & + & {
    border-left: 1px solid var(--sm-color-border);
  }

  &--active {
    background: var(--sm-color-bg-muted, #f1f1f1);
    color: var(--sm-color-text);
    font-weight: 600;
  }
}
</style>
