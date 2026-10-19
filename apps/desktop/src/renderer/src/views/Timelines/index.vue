<template>
  <div class="timelines">
    <div class="timelines__head">
      <h2>时间线</h2>
      <n-button size="small" type="primary" @click="editorOpen = true">新建时间线</n-button>
    </div>
    <p class="timelines__hint">时间线是按规则自动聚合的资源视图，不复制资源。</p>
    <div v-if="loading" class="timelines__empty">加载中…</div>
    <div v-else class="timelines__grid">
      <button type="button" class="timelines__all" @click="open('all')">
        <span class="timelines__all-title">全部媒体</span>
        <span class="timelines__all-meta">{{ allCount }} 项 · 图片 + 视频</span>
      </button>
      <CollectionCard
        v-for="card in cards"
        :key="card.id"
        :title="card.name"
        :member-count="card.count"
        :previews="card.previews"
        @open="open(String(card.id))"
      />
    </div>
    <TimelineEditorModal v-model:show="editorOpen" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import CollectionCard from '@/components/CollectionCard/index.vue'
import TimelineEditorModal from '@/components/TimelineEditorModal/index.vue'
import { notify } from '@/application/notify'
import { getPhotoTimeline, listSavedViews } from '@/infrastructure/http'
import type { PhotoTile } from '@/domain'
import { useLibraryStore } from '@/application/stores/library'

interface Card {
  id: number
  name: string
  count: number
  previews: string[]
}

const router = useRouter()
const library = useLibraryStore()
const cards = ref<Card[]>([])
const allCount = ref(0)
const loading = ref(false)
const editorOpen = ref(false)

function previewOf(tiles: PhotoTile[]): string[] {
  return tiles.slice(0, 3).flatMap((tile) => (tile.thumbnailPath ? [tile.thumbnailPath] : []))
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [views, all] = await Promise.all([
      listSavedViews(),
      getPhotoTimeline({ scope: 'media' }),
    ])
    allCount.value = all.total
    const next: Card[] = []
    for (const view of views) {
      const timeline = await getPhotoTimeline({
        scope: view.scope,
        imageRule: view.filters.image,
        videoRule: view.filters.video,
        tagIds: view.filters.tagIds,
        dateFrom: view.filters.dateFrom,
        dateTo: view.filters.dateTo,
        includeUntimed: view.filters.includeUntimed,
      })
      next.push({
        id: view.id,
        name: view.name,
        count: timeline.total,
        previews: previewOf([
          ...timeline.days.flatMap((day) => day.photos),
          ...timeline.unknownPhotos,
        ]),
      })
    }
    cards.value = next
  } catch (error) {
    notify.fromError(error, { context: '读取时间线' })
  } finally {
    loading.value = false
  }
}

function open(id: string): void {
  void router.push(`/timelines/${id}`)
}

watch(
  () => [
    library.savedViewsRevision,
    library.resourceRevision('image') + library.resourceRevision('video'),
    library.watchRevision,
  ],
  () => {
    void load()
  }
)

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.timelines {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.timelines__head {
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: 18px;
  }
}

.timelines__hint {
  margin: 8px 0 16px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.timelines__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.timelines__all {
  aspect-ratio: 4 / 3;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: linear-gradient(135deg, #1f2937, #4b5563);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-start;
  padding: 14px;
  cursor: pointer;
  text-align: left;
}

.timelines__all-title {
  font-size: 16px;
  font-weight: 600;
}

.timelines__all-meta {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.75;
}

.timelines__empty {
  padding: 20px;
  color: var(--sm-color-text-muted);
  font-size: 13px;
}
</style>
