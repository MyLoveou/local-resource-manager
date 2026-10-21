<template>
  <div class="map-detail">
    <header class="map-detail__head">
      <div>
        <h2>{{ title }}</h2>
        <p>{{ subtitle }}</p>
      </div>
      <div class="map-detail__actions">
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
          删除地图规则不会删除资源。
        </n-popconfirm>
        <n-button size="small" @click="router.push('/maps')">返回</n-button>
      </div>
    </header>
    <div class="map-detail__bar">
      <span>{{ scopeLabel }}</span>
    </div>
    <div class="map-detail__body">
      <PhotoMap
        :key="JSON.stringify(rules)"
        :scope="scope"
        :rules="rules"
      />
    </div>
    <TimelineEditorModal
      v-if="savedView"
      v-model:show="editOpen"
      kind="map"
      :view="savedView"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NPopconfirm } from 'naive-ui'
import PhotoMap from '@/components/PhotoMap/index.vue'
import TimelineEditorModal from '@/components/TimelineEditorModal/index.vue'
import { notify } from '@/application/notify'
import { deleteSavedView, getSavedView } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { SavedView, SavedViewFilters, TimelineScope } from '@/domain'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const savedView = ref<SavedView | null>(null)
const editOpen = ref(false)

const scope = computed<TimelineScope>(() => savedView.value?.scope ?? 'media')
const rules = computed<SavedViewFilters>(() => savedView.value?.filters ?? {
  image: { include: [], exclude: [] },
  video: { include: [], exclude: [] },
  tagIds: [],
  includeUntimed: true,
})
const title = computed(() => savedView.value?.name ?? '全部地图')
const scopeLabel = computed(() =>
  scope.value === 'media' ? '图片 + 视频' : scope.value === 'image' ? '图片' : '视频',
)
const subtitle = computed(() => {
  const filter = savedView.value?.filters
  if (!filter) return '当前加入地图的 GPS 图片'
  const dates = filter.dateFrom || filter.dateTo
    ? `${filter.dateFrom ?? '…'} ~ ${filter.dateTo ?? '…'}`
    : '不限日期'
  return `${dates} · 点击聚合点查看照片`
})

async function load(): Promise<void> {
  const raw = String(route.params.id ?? 'all')
  if (raw === 'all' || !Number.isFinite(Number(raw))) {
    savedView.value = null
    return
  }
  try {
    savedView.value = await getSavedView(Number(raw))
  } catch (error) {
    notify.fromError(error, { context: '读取地图规则' })
    void router.replace('/maps')
  }
}

function onSaved(next: SavedView): void {
  savedView.value = next
  library.invalidate({ savedViews: true, home: true })
}

async function remove(): Promise<void> {
  if (!savedView.value) return
  try {
    await deleteSavedView(savedView.value.id)
    library.invalidate({ savedViews: true, home: true })
    notify.toast.success('地图规则已删除')
    void router.push('/maps')
  } catch (error) {
    notify.fromError(error, { context: '删除地图规则' })
  }
}

watch(() => route.params.id, () => void load())

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.map-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.map-detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px 8px;

  h2 {
    margin: 0;
    font-size: 18px;
  }

  p {
    margin: 6px 0 0;
    color: var(--sm-color-text-muted);
    font-size: 12px;
  }
}

.map-detail__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.map-detail__bar {
  padding: 0 20px 8px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.map-detail__body {
  flex: 1;
  min-height: 0;
}
</style>
