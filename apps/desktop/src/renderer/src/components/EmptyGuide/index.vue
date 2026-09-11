<template>
  <div class="empty-guide">
    <slot />
    <p class="hint">
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    hint?: string
  }>(),
  { hint: '暂无资源' }
)
</script>

<style scoped lang="less">
@import '@/ui/styles/variables.less';

.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 100%;
  color: @text-muted;
}
</style>
