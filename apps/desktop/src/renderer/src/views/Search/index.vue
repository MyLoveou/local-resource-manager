<template>
  <div class="search-page">
    <p v-if="!q" class="search-page__hint">输入关键词搜索全库</p>
    <ResourceBrowser v-else empty-hint="无匹配" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'

const route = useRoute()
const browse = useBrowseQueryStore()
const q = computed(() => String(route.query.q ?? '').trim())

watch(
  q,
  (value) => {
    if (value) browse.patch(undefined, undefined, { q: value })
  },
  { immediate: true }
)
</script>

<style scoped lang="less">
.search-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.search-page__hint {
  padding: var(--sm-space-3);
  color: var(--sm-color-text-muted);
}
</style>
