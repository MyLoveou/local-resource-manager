<template>
  <div class="image-page">
    <ResourceBrowser type="anime" empty-hint="暂无番剧，请先在顶栏导入文件夹" />
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
