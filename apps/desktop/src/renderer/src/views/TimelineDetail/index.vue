<template>
  <div class="timeline-detail">
    <header class="timeline-detail__head">
      <div>
        <h2>{{ title }}</h2>
        <p>{{ subtitle }}</p>
      </div>
      <div class="timeline-detail__actions">
        <n-button v-if="savedView" size="small" @click="editOpen = true">编辑规则</n-button>
        <n-popconfirm
          v-if="savedView"
          positive-text="删除"
          negative-text="取消"
          @positive-click="remove"
        >
          <template #trigger>
            <n-button size="small" type="error" ghost>删除</n-button>
          </template>
          删除时间线不会删除资源。
        </n-popconfirm>
        <n-button size="small" @click="router.push('/timelines')">返回</n-button>
      </div>
    </header>
    <div class="timeline-detail__bar">
      <n-button-group size="small">
        <n-button :type="view === 'timeline' ? 'primary' : 'default'" @click="view = 'timeline'">
          时间线
        </n-button>
        <n-button :type="view === 'map' ? 'primary' : 'default'" @click="view = 'map'">
          地图
        </n-button>
      </n-button-group>
      <span class="timeline-detail__scope">{{ scopeLabel }}</span>
    </div>
    <div class="timeline-detail__body">
      <PhotoTimeline
        v-if="view === 'timeline'"
        :scope="scope"
        :rules="rules"
        hide-filters
      />
      <div v-else class="timeline-detail__map">
        <h3>地图</h3>
        <p>当前时间线的地图视图；完整 MapLibre 交互后续接入。</p>
      </div>
    </div>
    <TimelineEditorModal
      v-if="savedView"
      v-model:show="editOpen"
      :view="savedView"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NButtonGroup, NPopconfirm } from 'naive-ui'
import PhotoTimeline from '@/components/PhotoTimeline/index.vue'
import TimelineEditorModal from '@/components/TimelineEditorModal/index.vue'
import { notify } from '@/application/notify'
import { deleteSavedView, getSavedView } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { SavedView, SavedViewFilters, TimelineScope } from '@/domain'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const savedView = ref<SavedView | null>(null)
const view = ref<'timeline' | 'map'>('timeline')
const editOpen = ref(false)

const scope = computed<TimelineScope>(() => savedView.value?.scope ?? 'media')
const rules = computed<SavedViewFilters>(() => savedView.value?.filters ?? {
  image: { include: [], exclude: [] },
  video: { include: [], exclude: [] },
  tagIds: [],
  includeUntimed: false,
})
const title = computed(() => savedView.value?.name ?? '全部媒体')
const scopeLabel = computed(() =>
  scope.value === 'media' ? '图片 + 视频' : scope.value === 'image' ? '图片' : '视频'
)
const subtitle = computed(() => {
  const filter = savedView.value?.filters
  if (!filter) return '按时间聚合的图片 + 视频'
  const dates = filter.dateFrom || filter.dateTo
    ? `${filter.dateFrom ?? '…'} ~ ${filter.dateTo ?? '…'}`
    : '全部时间'
  return `${scopeLabel.value} · ${dates}`
})

async function load(): Promise<void> {
  const raw = String(route.params.id ?? 'all')
  if (raw === 'all') {
    savedView.value = null
    return
  }
  try {
    savedView.value = await getSavedView(Number(raw))
  } catch (error) {
    notify.fromError(error, { context: '读取时间线' })
    void router.replace('/timelines')
  }
}

function onSaved(next: SavedView): void {
  savedView.value = next
}

async function remove(): Promise<void> {
  if (!savedView.value) return
  try {
    await deleteSavedView(savedView.value.id)
    library.invalidate({ savedViews: true, home: true })
    notify.toast.success('时间线已删除')
    void router.push('/timelines')
  } catch (error) {
    notify.fromError(error, { context: '删除时间线' })
  }
}

watch(() => route.params.id, () => {
  void load()
})

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.timeline-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.timeline-detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px 8px;

  h2 {
    margin: 0;
    font-size: 18px;
  }

  p {
    margin: 4px 0 0;
    color: var(--sm-color-text-muted);
    font-size: 12px;
  }
}

.timeline-detail__actions {
  display: flex;
  gap: 8px;
}

.timeline-detail__bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px 8px;
}

.timeline-detail__scope {
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.timeline-detail__body {
  flex: 1;
  min-height: 0;
}

.timeline-detail__map {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--sm-color-text-muted);
  font-size: 13px;
}
</style>
