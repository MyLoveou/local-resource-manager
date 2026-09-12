<template>
  <div class="trash-page">
    <ResourceBrowser status="trashed" empty-hint="回收站是空的" />
  </div>
</template>

<script setup lang="ts">
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'
</script>

<style scoped lang="less">
.trash-page {
  height: 100%;
  min-height: 0;
}
</style>
