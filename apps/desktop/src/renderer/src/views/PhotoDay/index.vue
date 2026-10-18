<template>
  <div class="photo-day">
    <div class="photo-day__head">
      <n-button size="small" @click="back">返回时间线</n-button>
      <h2 class="photo-day__title">{{ title }}</h2>
    </div>
    <ResourceBrowser
      :empty-hint="emptyHint"
      timeline-media
      hide-controls
      :taken-date="takenDate"
      :untimed="untimed"
      :timeline-visible="includeAll ? undefined : true"
      :include-collected-override="true"
      :category-id-override="categoryId"
      :tag-ids-override="tagIds"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'

const route = useRoute()
const router = useRouter()

const rawDate = computed(() => String(route.params.date ?? ''))
const isUnknown = computed(() => rawDate.value === 'unknown')
const takenDate = computed(() => (isUnknown.value ? undefined : rawDate.value))
const untimed = computed(() => isUnknown.value)
const includeAll = computed(() => route.query.includeAll === '1')
const categoryId = computed(() =>
  route.query.categoryId ? Number(route.query.categoryId) : null
)
const tagIds = computed(() =>
  route.query.tagIds
    ? String(route.query.tagIds).split(',').flatMap((value) => {
        const id = Number(value)
        return Number.isFinite(id) ? [id] : []
      })
    : []
)
const title = computed(() => (isUnknown.value ? '未知时间' : rawDate.value))
const emptyHint = computed(() =>
  isUnknown.value ? '没有未知时间的照片。' : '这一天没有符合条件的照片。'
)

function back(): void {
  const query: Record<string, string> = {}
  if (includeAll.value) query.includeAll = '1'
  if (categoryId.value !== null) query.categoryId = String(categoryId.value)
  if (tagIds.value.length > 0) query.tagIds = tagIds.value.join(',')
  void router.push({ path: '/photos', query })
}
</script>

<style scoped lang="less">
.photo-day {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.photo-day__head {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  padding: var(--sm-space-2);
  flex-shrink: 0;
}

.photo-day__title {
  font-size: 16px;
  margin: 0;
}
</style>
