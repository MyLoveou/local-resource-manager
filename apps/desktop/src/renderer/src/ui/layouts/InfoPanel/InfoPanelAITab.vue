<template>
  <section class="info-panel-section info-panel-ai-empty">
    <div class="info-panel-section-title">AI</div>
    <p>在 AI 中心可以搜索、分析和管理模型；也可以从当前图片直接找相似。</p>
    <div class="info-panel-ai-actions">
      <n-button v-if="isImage" size="small" @click="emit('similar')">找相似</n-button>
      <n-button size="small" @click="emit('open-ai')">打开 AI 中心</n-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'

defineProps<{ isImage: boolean }>()
const emit = defineEmits<{ similar: []; 'open-ai': [] }>()
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

.info-panel-ai-empty p {
  margin: 8px 0 12px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
  line-height: 1.7;
}

.info-panel-ai-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
