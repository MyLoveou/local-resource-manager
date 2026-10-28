<template>
  <div class="episode-list">
    <div class="episode-list__bar">
      <span class="episode-list__hint">{{ summary }}</span>
      <button type="button" class="episode-list__action" :disabled="busy" @click="backfill">
        补封面
      </button>
    </div>

    <section v-for="season in seasons" :key="season.id ?? season.seasonNumber">
      <div class="episode-list__label">第 {{ season.seasonNumber }} 季</div>
      <div class="episode-list__grid">
        <button
          v-for="ep in season.episodes ?? []"
          :key="ep.fileId"
          type="button"
          class="episode-card"
          @click="$emit('play', ep.fileId)"
        >
          <img v-if="ep.coverUrl" class="episode-card__cover" :src="ep.coverUrl" alt="" />
          <div v-else class="episode-card__cover episode-card__cover--empty">EP</div>
          <div class="episode-card__meta">
            <span class="episode-card__no">{{ pad(ep.episodeNumber) }}</span>
            <span v-if="ep.hasSubtitles" class="episode-card__sub" title="有字幕">字幕</span>
          </div>
        </button>
      </div>
    </section>

    <template v-if="extras.length">
      <div class="episode-list__label">特典</div>
      <div class="episode-list__extras">
        <button
          v-for="extra in extras"
          :key="extra.fileId"
          type="button"
          class="episode-card episode-card--extra"
          @click="$emit('play', extra.fileId)"
        >
          <span>{{ extra.title || '特典' }}</span>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { backfillCovers } from '@/infrastructure/http/seriesAssets'
import { notify } from '@/application/notify'
import type { SeriesEpisode, SeriesExtra, SeriesSeason } from '@/domain'

const props = defineProps<{
  resourceId?: number
  seasons: SeriesSeason[]
  extras: SeriesExtra[]
}>()

defineEmits<{ play: [fileId: number] }>()

const busy = ref(false)

const episodes = computed(() =>
  props.seasons.flatMap((season) => season.episodes ?? []),
)
const withCover = computed(() => episodes.value.filter((ep: SeriesEpisode) => ep.hasCover).length)
const withSubs = computed(() => episodes.value.filter((ep: SeriesEpisode) => ep.hasSubtitles).length)

const summary = computed(() => {
  const total = episodes.value.length
  if (!total) return '暂无集'
  return `${total} 集 · 封面 ${withCover.value} · 字幕 ${withSubs.value}`
})

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

async function backfill(): Promise<void> {
  if (props.resourceId == null || busy.value) return
  busy.value = true
  try {
    const result = await backfillCovers(props.resourceId)
    if (result.generated === 0 && result.failed === 0) {
      notify.toast.info('所有集都已有封面')
    } else {
      notify.toast.success(`补了 ${result.generated} 集封面，失败 ${result.failed} 集`)
    }
  } catch {
    notify.toast.error('补封面失败')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="less">
.episode-list__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.episode-list__hint {
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}

.episode-list__action {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--sm-color-border);
  background: var(--sm-color-bg-surface);
  color: inherit;
  cursor: pointer;
}

.episode-list__label {
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
  margin: 8px 0 4px;
}

.episode-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
  gap: 6px;
}

.episode-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0;
  border: 1px solid var(--sm-color-border);
  border-radius: 6px;
  background: var(--sm-color-bg-surface);
  color: inherit;
  cursor: pointer;
  overflow: hidden;
}

.episode-card__cover {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--sm-color-bg-muted, #eee);
}

.episode-card__cover--empty {
  display: grid;
  place-items: center;
  font-size: 11px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.episode-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px;
  font-size: 11px;
}

.episode-card__sub {
  color: var(--sm-color-primary, #2f6fed);
}

.episode-list__extras {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.episode-card--extra {
  flex-direction: row;
  padding: 4px 8px;
  font-size: 11px;
}
</style>
