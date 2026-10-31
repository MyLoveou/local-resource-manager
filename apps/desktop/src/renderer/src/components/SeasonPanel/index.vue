<template>
  <div class="season-panel">
    <p class="season-panel__summary">{{ summary }}</p>
    <div v-if="seasons.length > 1 || extrasCount" class="season-panel__tabs">
      <button
        v-for="item in seasons"
        :key="item.seasonNumber"
        type="button"
        :class="['season-panel__tab', { 'is-active': item.seasonNumber === season }]"
        @click="seasonNumber = item.seasonNumber"
      >
        第 {{ item.seasonNumber }} 季
        <span v-if="!item.catalog && !item.coverUrl" class="season-panel__tab-badge">未刮</span>
      </button>
      <button
        v-if="extrasCount"
        type="button"
        class="season-panel__tab"
        :class="{ 'is-active': extraTabActive }"
        @click="extraTabActive = !extraTabActive"
      >
        特典 {{ extrasCount }}
      </button>
    </div>

    <p v-if="extraTabActive" class="season-panel__hint">
      特典不单独刮削；在系列详情页可以逐条查看与播放。
    </p>

    <template v-if="current">
      <img
        v-if="coverSrc"
        class="season-panel__cover"
        :src="resolveLibraryMediaUrl(coverSrc)"
        alt=""
      />
      <div v-else class="season-panel__cover season-panel__cover--empty">无封面</div>

      <dl class="season-panel__meta">
        <dt v-if="current.title">季</dt>
        <dd v-if="current.title">{{ current.title }}</dd>
        <dt v-if="nameCn">中文名</dt>
        <dd v-if="nameCn">{{ nameCn }}</dd>
        <dt v-if="catalog?.originalTitle">原名</dt>
        <dd v-if="catalog?.originalTitle">{{ catalog.originalTitle }}</dd>
        <dt v-if="catalog?.date">放送</dt>
        <dd v-if="catalog?.date">{{ catalog.date }}</dd>
        <dt>集数</dt>
        <dd>{{ siteEps }} / 本地 {{ current.episodes?.length ?? 0 }}</dd>
        <dt v-if="catalog?.siteScore">评分</dt>
        <dd v-if="catalog?.siteScore">{{ catalog.siteScore.toFixed(1) }}</dd>
      </dl>

      <p v-if="current.synopsis" class="season-panel__synopsis">{{ current.synopsis }}</p>
      <p v-else class="season-panel__hint">这一季还没有简介。</p>

      <button type="button" class="season-panel__action" @click="scrapeOpen = true">
        刮削本季
      </button>
    </template>
    <p v-else class="season-panel__hint">这部作品还没有季。</p>

    <SeasonScrape
      v-if="resourceId != null"
      v-model:show="scrapeOpen"
      :resource-id="resourceId"
      :season="seasonNumber"
      :season-title="current?.title ?? null"
      :fallback-title="fallbackTitle"
      @applied="emit('refresh')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SeasonScrape from '@/components/SeasonScrape/index.vue'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'
import type { SeriesSeason } from '@/domain'

const props = defineProps<{
  resourceId?: number
  seasons: SeriesSeason[]
  /** 外部（详情页选中某一集）指定的季 */
  season: number
  fallbackTitle?: string | null
  /** 作品封面：季封面缺失时回退 */
  resourceCover?: string | null
  /** 特典作为最后一个标签 */
  extras?: { title?: string | null; fileId: number }[]
}>()

const emit = defineEmits<{ refresh: []; 'update:season': [number] }>()

const seasonNumber = ref(props.season || props.seasons[0]?.seasonNumber || 1)
const scrapeOpen = ref(false)

watch(
  () => props.season,
  (next) => {
    if (next && next !== seasonNumber.value) seasonNumber.value = next
  },
)
watch(seasonNumber, (next) => emit('update:season', next))
watch(
  () => props.seasons.length,
  () => {
    if (!props.seasons.some((item) => item.seasonNumber === seasonNumber.value)) {
      seasonNumber.value = props.seasons[0]?.seasonNumber ?? 1
    }
  },
)

const extraTabActive = ref(false)

const extrasCount = computed(() => props.extras?.length ?? 0)

const totalEpisodes = computed(() =>
  props.seasons.reduce((sum, item) => sum + (item.episodes?.length ?? 0), 0),
)

const scrapedSeasons = computed(
  () => props.seasons.filter((item) => item.catalog || item.coverUrl).length,
)

const summary = computed(
  () =>
    `${props.seasons.length} 季 · ${totalEpisodes.value} 集` +
    (scrapedSeasons.value ? ` · 已刮 ${scrapedSeasons.value} 季` : ''),
)

const coverSrc = computed(
  () => current.value?.coverUrl || props.resourceCover || null,
)

const current = computed(
  () => props.seasons.find((item) => item.seasonNumber === seasonNumber.value) ?? null,
)
const catalog = computed(() => current.value?.catalog ?? null)
const nameCn = computed(() => catalog.value?.nameCn ?? null)
const siteEps = computed(() => catalog.value?.eps ?? catalog.value?.totalEpisodes ?? '—')
</script>

.season-panel__summary {
  margin: 0;
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}

.season-panel__tab-badge {
  margin-left: 4px;
  font-size: 10px;
  opacity: 0.7;
}

<style scoped lang="less">
.season-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.season-panel__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.season-panel__tab {
  border: 1px solid var(--sm-color-border);
  background: transparent;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}

.season-panel__tab.is-active {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
}

.season-panel__cover {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  border-radius: 6px;
}

.season-panel__cover--empty {
  display: grid;
  place-items: center;
  height: 90px;
  font-size: 12px;
  color: var(--sm-color-text-muted, #9ca3af);
  background: var(--sm-color-bg-muted, #eee);
}

.season-panel__meta {
  display: grid;
  grid-template-columns: 46px 1fr;
  gap: 2px 8px;
  margin: 0;
  font-size: 12px;
}

.season-panel__meta dt {
  color: var(--sm-color-text-muted, #6b7280);
}

.season-panel__meta dd {
  margin: 0;
  word-break: break-all;
}

.season-panel__synopsis {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--sm-color-text-muted, #6b7280);
}

.season-panel__hint {
  margin: 0;
  font-size: 12px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.season-panel__action {
  align-self: flex-start;
  border: 1px solid var(--sm-color-border);
  background: transparent;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}
</style>
