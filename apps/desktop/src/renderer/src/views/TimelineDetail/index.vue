<template>
  <div class="timeline-detail">
    <header class="timeline-detail__head">
      <div>
        <h2>{{ title }}</h2>
        <p>{{ subtitle }}</p>
        <div v-if="viewNote" class="timeline-detail__note">
          <strong v-if="viewNote.title">{{ viewNote.title }}</strong>
          <span v-if="viewNote.locationName">{{ viewNote.locationName }}</span>
          <p v-if="viewNote.body">{{ viewNote.body }}</p>
        </div>
      </div>
      <div class="timeline-detail__actions">
        <n-button v-if="savedView" size="small" @click="noteOpen = true">备注</n-button>
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
      <span class="timeline-detail__scope">{{ scopeLabel }}</span>
      <n-button-group size="small">
        <n-button :type="layout === 'stream' ? 'primary' : 'default'" @click="setLayout('stream')">
          时间线
        </n-button>
        <n-button :type="layout === 'grid' ? 'primary' : 'default'" @click="setLayout('grid')">
          网格
        </n-button>
      </n-button-group>
    </div>
    <div class="timeline-detail__body">
      <PhotoTimeline
        :scope="scope"
        :rules="rules"
        :layout="layout"
        hide-filters
      />
    </div>
    <TimelineEditorModal
      v-if="savedView"
      v-model:show="editOpen"
      :view="savedView"
      @saved="onSaved"
    />
    <TimelineNoteModal
      v-if="savedView"
      v-model:show="noteOpen"
      :saved-view-id="savedView.id"
      :note="viewNote"
      @saved="onNoteSaved"
      @deleted="viewNote = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NButtonGroup, NPopconfirm } from 'naive-ui'
import PhotoTimeline from '@/components/PhotoTimeline/index.vue'
import TimelineEditorModal from '@/components/TimelineEditorModal/index.vue'
import TimelineNoteModal from '@/components/TimelineNoteModal/index.vue'
import { notify } from '@/application/notify'
import { deleteSavedView, getSavedView, getSavedViewNote, type TimelineNote } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { SavedView, SavedViewFilters, TimelineScope } from '@/domain'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const savedView = ref<SavedView | null>(null)
const viewNote = ref<TimelineNote | null>(null)
const editOpen = ref(false)
const noteOpen = ref(false)
const layout = ref<'stream' | 'grid'>('stream')

function setLayout(next: 'stream' | 'grid'): void {
  layout.value = next
  const query = { ...route.query }
  if (next === 'grid') query.view = 'grid'
  else delete query.view
  void router.replace({ query })
}

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
    viewNote.value = null
    return
  }
  try {
    const view = await getSavedView(Number(raw))
    savedView.value = view
    viewNote.value = null
    if (view.id != null) {
      try {
        viewNote.value = await getSavedViewNote(view.id)
      } catch (error) {
        notify.fromError(error, { context: '读取时间线备注' })
      }
    }
  } catch (error) {
    notify.fromError(error, { context: '读取时间线' })
    void router.replace('/timelines')
  }
}

function onSaved(next: SavedView): void {
  savedView.value = next
}

function onNoteSaved(note: TimelineNote): void {
  viewNote.value = note
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

watch(
  () => route.query.view,
  (raw) => {
    layout.value = raw === 'grid' ? 'grid' : 'stream'
  },
  { immediate: true },
)

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

.timeline-detail__note {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 10px;
  margin-top: 8px;
  padding: 8px 10px;
  border-left: 3px solid var(--sm-color-primary, #6366f1);
  background: var(--sm-color-bg-muted, #f5f5f5);
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;

  strong {
    font-size: 13px;
  }

  span {
    color: var(--sm-color-text-muted);
  }

  p {
    flex-basis: 100%;
    margin: 0;
    color: var(--sm-color-text-muted);
    white-space: pre-wrap;
  }
}

.timeline-detail__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
</style>
