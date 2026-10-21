<template>
  <div class="maps">
    <div class="maps__head">
      <h2>地图</h2>
      <n-button size="small" type="primary" @click="editorOpen = true">新建地图规则</n-button>
    </div>
    <p class="maps__hint">地图是按 GPS 自动聚合的资源视图，不复制资源；只有加入地图且带 GPS 的图片/视频会显示。</p>
    <div v-if="loading" class="maps__empty">加载中…</div>
    <div v-else class="maps__grid">
      <button type="button" class="maps__all" @click="open('all')">
        <span class="maps__all-title">全部地图</span>
        <span class="maps__all-meta">{{ allCount }} 项 · 图片 + 视频</span>
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
    <TimelineEditorModal
      v-model:show="editorOpen"
      kind="map"
      @saved="load"
    />
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

function mapQuery(filters?: {
  scope?: 'image' | 'video' | 'media'
  image?: { include: number[]; exclude: number[] }
  video?: { include: number[]; exclude: number[] }
  tagIds?: number[]
  dateFrom?: string | null
  dateTo?: string | null
}) {
  return {
    scope: filters?.scope ?? 'media',
    includeAll: true,
    imageRule: filters?.image,
    videoRule: filters?.video,
    tagIds: filters?.tagIds?.length ? filters.tagIds : undefined,
    dateFrom: filters?.dateFrom,
    dateTo: filters?.dateTo,
    includeUntimed: true,
    mapVisible: true,
    mapOnly: true,
  } as const
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [views, all] = await Promise.all([
      listSavedViews(undefined, 'map'),
      getPhotoTimeline(mapQuery()),
    ])
    allCount.value = all.total
    const next: Card[] = []
    for (const view of views) {
      const timeline = await getPhotoTimeline(mapQuery({ scope: view.scope, ...view.filters }))
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
    notify.fromError(error, { context: '读取地图' })
  } finally {
    loading.value = false
  }
}

function open(id: string): void {
  void router.push(`/maps/${id}`)
}

watch(
  () => [
    library.savedViewsRevision,
    library.resourceRevision('image') + library.resourceRevision('video'),
    library.watchRevision,
  ],
  () => {
    void load()
  },
)

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.maps {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.maps__head {
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: 18px;
  }
}

.maps__hint {
  margin: 8px 0 16px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.maps__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.maps__all {
  aspect-ratio: 4 / 3;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: linear-gradient(135deg, #065f46, #0f766e);
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-start;
  padding: 14px;
  cursor: pointer;
  text-align: left;
}

.maps__all-title {
  font-size: 16px;
  font-weight: 600;
}

.maps__all-meta {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.75;
}

.maps__empty {
  padding: 20px;
  color: var(--sm-color-text-muted);
  font-size: 13px;
}
</style>
