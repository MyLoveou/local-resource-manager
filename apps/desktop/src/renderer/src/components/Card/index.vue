<template>
  <n-card hoverable size="small" class="resource-card" :content-style="{ padding: '8px 10px' }">
    <template #cover>
      <div class="cover">
        <img
          v-if="coverUrl"
          :src="coverUrl"
          :alt="title ?? '封面'"
          class="cover-img"
          loading="lazy"
          decoding="async"
        >
        <div v-else class="cover-placeholder">无封面</div>
      </div>
    </template>
    <div class="title" :title="title">{{ title }}</div>
  </n-card>
</template>

<script setup lang="ts">
import { NCard } from 'naive-ui'

defineProps<{
  /** 标题 */
  title?: string
  /** 封面 URL */
  coverUrl?: string
}>()
</script>

<style scoped lang="less">
.resource-card {
  width: 100%;
  overflow: hidden;

  .cover {
    aspect-ratio: 3 / 4;
    background: var(--n-color-embedded, #f5f5f5);
  }

  .cover-img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .cover-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--n-text-color-3, #999);
    font-size: 12px;
  }

  .title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
    line-height: 1.4;
    text-align: left;
  }
}
</style>
