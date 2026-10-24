<template>
  <div class="type-tabs">
    <button
      v-for="profile in profiles"
      :key="profile.type"
      type="button"
      class="type-tabs__item"
      :class="{ 'type-tabs__item--active': profile.type === type }"
      @click="$emit('change', profile.type)"
    >
      {{ profile.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TYPE_PROFILES, type ResourceType } from '@/domain'
import { isSectionHidden } from '@/domain/visibility'

defineProps<{ type: ResourceType }>()
defineEmits<{ change: [type: ResourceType] }>()

const profiles = computed(() =>
  TYPE_PROFILES.filter((profile) => !isSectionHidden(profile.routePath)),
)
</script>

<style scoped lang="less">
.type-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px 0;
  overflow-x: auto;
}

.type-tabs__item {
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--sm-color-text-muted);
  padding: 6px 10px;
  font-size: 13px;
  cursor: pointer;

  &--active {
    color: var(--sm-color-text);
    border-bottom-color: var(--sm-color-accent, #2563eb);
    font-weight: 600;
  }
}
</style>
