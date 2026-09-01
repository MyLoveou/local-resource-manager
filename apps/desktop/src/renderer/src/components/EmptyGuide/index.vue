<template>
  <div class="empty-guide">
    <slot />
    <p class="hint">
      暂无资源
    </p>
  </div>
</template>

<script setup lang="ts">
// 空状态引导组件（首页无资源目录时展示）—— 结构占位
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
