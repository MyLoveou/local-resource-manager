<template>
  <div class="video-page">
    <ResourceBrowser type="video" empty-hint="暂无视频" />
  </div>
</template>

<script setup lang="ts">
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'
</script>

<style scoped lang="less">
.video-page {
  height: 100%;
  min-height: 0;
}
</style>
