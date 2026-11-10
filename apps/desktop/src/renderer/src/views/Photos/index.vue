<template>
  <div class="photos">
    <div class="photos__head">
      <h2 class="photos__title">时间线</h2>
      <n-button-group size="small">
        <n-button :type="mode === 'timeline' ? 'primary' : 'default'" @click="mode = 'timeline'">
          时间线
        </n-button>
        <n-button :type="mode === 'grid' ? 'primary' : 'default'" @click="mode = 'grid'">
          网格
        </n-button>
      </n-button-group>
    </div>
    <div class="photos__body">
      <PhotoTimeline v-if="mode === 'timeline'" @open-day="openDay" />
      <ResourceBrowser
        v-else
        timeline-media
        empty-hint="还没有照片或视频。顶栏导入后可在网格或时间线查看。"
        :include-collected-override="true"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NButtonGroup } from 'naive-ui'
import PhotoTimeline from '@/components/PhotoTimeline/index.vue'
import ResourceBrowser from '@/components/ResourceBrowser/index.vue'

const router = useRouter()
const mode = ref<'timeline' | 'grid'>('timeline')

function openDay(payload: {
  date: string | null
  includeAll: boolean
  categoryIds: number[]
  tagIds: number[]
}): void {
  const query: Record<string, string> = {}
  if (payload.includeAll) query.includeAll = '1'
  if (payload.categoryIds.length > 0) query.categoryIds = payload.categoryIds.join(',')
  if (payload.tagIds.length > 0) query.tagIds = payload.tagIds.join(',')
  void router.push({
    path: `/library/image/day/${payload.date ?? 'unknown'}`,
    query,
  })
}
</script>

<style scoped lang="less">
.photos {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.photos__head {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  padding: var(--sm-space-2);
  flex-shrink: 0;
}

.photos__title {
  font-size: 16px;
  margin: 0;
}

.photos__body {
  flex: 1;
  min-height: 0;
}
</style>
