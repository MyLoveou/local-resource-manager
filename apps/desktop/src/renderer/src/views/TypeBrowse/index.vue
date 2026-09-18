<template>
  <div class="type-browse">
    <ResourceBrowser :key="type" :type="type" :empty-hint="emptyHint" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'
import { profileFor, type ResourceType } from '@/domain'

const route = useRoute()
const type = computed(() => route.meta.resourceType as ResourceType)
const emptyHint = computed(() => profileFor(type.value)?.emptyHint ?? '暂无资源，请先在顶栏导入')
</script>

<style scoped lang="less">
.type-browse {
  height: 100%;
  min-height: 0;
}
</style>
