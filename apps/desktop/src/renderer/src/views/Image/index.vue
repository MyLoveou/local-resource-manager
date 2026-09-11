<template>
  <div class="image-page">
    <ResourceBrowser type="image" empty-hint="暂无图片，请先在顶栏导入" />
  </div>
</template>

<script setup lang="ts">
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'
</script>

<style scoped lang="less">
.image-page {
  height: 100%;
  min-height: 0;
}
</style>
