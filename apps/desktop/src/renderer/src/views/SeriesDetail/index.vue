<template>
  <div class="series-detail">
    <header class="series-detail__head">
      <button type="button" class="series-detail__back" @click="goBack">← 返回</button>
      <h1 class="series-detail__title">{{ resource?.title || '加载中…' }}</h1>
      <span v-if="counts" class="series-detail__counts">{{ counts }}</span>
    </header>

    <p v-if="error" class="series-detail__error">
      {{ error }}
      <button type="button" @click="load">重试</button>
    </p>

    <div v-else-if="resource" class="series-detail__body">
      <aside class="series-detail__aside">
        <img
          v-if="coverSrc"
          class="series-detail__cover"
          :src="coverSrc"
          alt=""
        />
        <div v-else class="series-detail__cover series-detail__cover--empty">无封面</div>
        <dl class="series-detail__meta">
          <dt v-if="resource.sourceName">原始名</dt>
          <dd v-if="resource.sourceName">{{ resource.sourceName }}</dd>
          <dt>类型</dt>
          <dd>{{ resource.type === 'av' ? 'AV' : '番剧' }}</dd>
        </dl>
      </aside>

      <main class="series-detail__main">
        <EpisodeList
          v-if="resource.id != null"
          :resource-id="resource.id"
          :seasons="resource.seasons ?? []"
          :extras="resource.extras ?? []"
          allow-scrape
          show-season-meta
          selectable
          :selected-file-id="selectedFileId"
          @play="playEpisode"
          @scrape="openSeasonScrape"
          @select="onSelectEpisode"
          @season-open="openSeasonPanel"
          @refresh="load"
        />
        <p v-if="!hasEpisodes" class="series-detail__hint">
          该作品还没有集数据。可以回到库中重新导入，或先用「补封面」生成封面。
        </p>
      </main>
      <SeasonScrape
        v-model:show="scrapeOpen"
        :resource-id="resource.id ?? 0"
        :season="scrapeSeason"
        :season-title="scrapeSeasonTitle"
        :fallback-title="resource?.title ?? null"
        @applied="load"
      />
    </div>

      <aside v-if="panelOpen" class="series-detail__panel">
        <header class="series-detail__panel-head">
          <strong>{{ panelSeasonLabel }}</strong>
          <button type="button" class="series-detail__panel-close" @click="panelOpen = false">×</button>
        </header>

        <div class="series-detail__panel-tabs">
          <button
            v-for="item in resource?.seasons ?? []"
            :key="item.seasonNumber"
            type="button"
            :class="['series-detail__panel-tab', { 'is-active': item.seasonNumber === panelSeason }]"
            @click="panelSeason = item.seasonNumber"
          >
            第 {{ item.seasonNumber }} 季
          </button>
        </div>

        <div v-if="panelSeasonData" class="series-detail__panel-body">
          <img
            v-if="panelSeasonData.coverUrl"
            class="series-detail__panel-cover"
            :src="resolveLibraryMediaUrl(panelSeasonData.coverUrl)"
            alt=""
          />
          <dl class="series-detail__panel-meta">
            <dt v-if="panelCatalog?.nameCn">中文名</dt>
            <dd v-if="panelCatalog?.nameCn">{{ panelCatalog.nameCn }}</dd>
            <dt v-if="panelCatalog?.originalTitle">原名</dt>
            <dd v-if="panelCatalog?.originalTitle">{{ panelCatalog.originalTitle }}</dd>
            <dt v-if="panelCatalog?.date">放送</dt>
            <dd v-if="panelCatalog?.date">{{ panelCatalog.date }}</dd>
            <dt>集数</dt>
            <dd>
              {{ panelCatalog?.eps ?? panelCatalog?.totalEpisodes ?? '—' }} / 本地
              {{ panelSeasonData.episodes?.length ?? 0 }}
            </dd>
            <dt v-if="panelCatalog?.siteScore">评分</dt>
            <dd v-if="panelCatalog?.siteScore">{{ panelCatalog.siteScore.toFixed(1) }}</dd>
          </dl>
          <p v-if="panelSeasonData.synopsis" class="series-detail__panel-synopsis">
            {{ panelSeasonData.synopsis }}
          </p>
          <p v-else class="series-detail__hint">这一季还没有简介，可以点下面的按钮刮削。</p>
          <button type="button" class="series-detail__panel-action" @click="openSeasonScrape(panelSeason)">
            刮削本季
          </button>
        </div>
      </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EpisodeList from '@/components/EpisodeList/index.vue'
import SeasonScrape from '@/components/SeasonScrape/index.vue'
import { getResource, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { openResource } from '@/infrastructure/consume/consumeResource'
import type { Resource } from '@/domain'

const route = useRoute()
const router = useRouter()

const resource = ref<Resource | null>(null)
const error = ref('')
const scrapeOpen = ref(false)
const scrapeSeason = ref(1)
const scrapeSeasonTitle = computed(() => {
  const season = (resource.value?.seasons ?? []).find((item) => item.seasonNumber === scrapeSeason.value)
  return season?.title ?? null
})

const panelOpen = ref(false)
const panelSeason = ref(1)
const selectedFileId = ref<number | null>(null)

const panelSeasonData = computed(
  () => (resource.value?.seasons ?? []).find((item) => item.seasonNumber === panelSeason.value) ?? null,
)
const panelCatalog = computed(() => panelSeasonData.value?.catalog ?? null)
const panelSeasonLabel = computed(
  () => panelSeasonData.value?.title || `第 ${panelSeason.value} 季`,
)

function openSeasonPanel(seasonNumber: number): void {
  panelSeason.value = seasonNumber
  panelOpen.value = true
}

/** 第一次点选中并开面板，再点同一集才播放 */
function onSelectEpisode(seasonNumber: number, fileId: number): void {
  if (selectedFileId.value === fileId) {
    void playEpisode(fileId)
    return
  }
  selectedFileId.value = fileId
  openSeasonPanel(seasonNumber)
}

function openSeasonScrape(seasonNumber: number): void {
  scrapeSeason.value = seasonNumber
  scrapeOpen.value = true
}

const coverSrc = computed(() => {
  const row = resource.value
  if (!row) return ''
  const raw = row.coverUrl || row.thumbnailPath
  return raw ? resolveLibraryMediaUrl(raw) : ''
})

const episodeFileIds = computed(() =>
  (resource.value?.seasons ?? []).flatMap((season) =>
    (season.episodes ?? []).map((episode) => episode.fileId),
  ),
)

const hasEpisodes = computed(() => episodeFileIds.value.length > 0)

const counts = computed(() => {
  if (!resource.value) return ''
  const seasons = resource.value.seasons ?? []
  const episodes = episodeFileIds.value.length
  const extras = (resource.value.extras ?? []).length
  if (!seasons.length && !extras) return ''
  return `${seasons.length} 季 · ${episodes} 集 · ${extras} 特典`
})

async function load(): Promise<void> {
  const id = Number(route.params.id)
  error.value = ''
  if (!Number.isFinite(id) || id <= 0) {
    error.value = '作品不存在'
    return
  }
  try {
    resource.value = await getResource(id)
  } catch {
    resource.value = null
    error.value = '作品不存在或加载失败'
  }
}

async function playEpisode(fileId: number): Promise<void> {
  const row = resource.value
  if (!row) return
  await openResource(row, { playlist: episodeFileIds.value, fileId })
}

function goBack(): void {
  if (window.history.length > 1) router.back()
  else void router.push('/library/anime')
}

function onKey(event: KeyboardEvent): void {
  if (event.key === 'Escape') goBack()
}

watch(() => route.params.id, load, { immediate: true })
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

.series-detail__panel {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 8px;
  max-height: 100%;
  overflow: auto;
}

.series-detail__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
}

.series-detail__panel-close {
  border: none;
  background: transparent;
  font-size: 16px;
  cursor: pointer;
  color: inherit;
}

.series-detail__panel-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.series-detail__panel-tab {
  border: 1px solid var(--sm-color-border);
  background: transparent;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}

.series-detail__panel-tab.is-active {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
}

.series-detail__panel-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 6px;
}

.series-detail__panel-meta {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 2px 8px;
  margin: 0;
  font-size: 12px;
}

.series-detail__panel-meta dt {
  color: var(--sm-color-text-muted, #6b7280);
}

.series-detail__panel-meta dd {
  margin: 0;
  word-break: break-all;
}

.series-detail__panel-synopsis {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--sm-color-text-muted, #6b7280);
}

.series-detail__panel-action {
  border: 1px solid var(--sm-color-border);
  background: transparent;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}
<style scoped lang="less">
.series-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  padding: 16px;
  overflow: auto;
}

.series-detail__head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.series-detail__back {
  border: 1px solid var(--sm-color-border);
  background: var(--sm-color-bg-surface);
  color: inherit;
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
}

.series-detail__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.series-detail__counts {
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}

.series-detail__body {
  display: flex;
  gap: 16px;
  min-height: 0;
}

.series-detail__aside {
  width: 200px;
  flex-shrink: 0;
}

.series-detail__cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 8px;
  background: var(--sm-color-bg-muted, #eee);
}

.series-detail__cover--empty {
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.series-detail__meta {
  margin: 10px 0 0;
  font-size: 12px;
}

.series-detail__meta dt {
  color: var(--sm-color-text-muted, #6b7280);
  margin-top: 6px;
}

.series-detail__meta dd {
  margin: 2px 0 0;
  word-break: break-all;
}

.series-detail__main {
  flex: 1;
  min-width: 0;
}

.series-detail__hint,
.series-detail__error {
  font-size: 13px;
  color: var(--sm-color-text-muted, #6b7280);
}
</style>
