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
        <div v-for="ep in season.episodes ?? []" :key="ep.fileId" class="episode-card-wrap">
          <button type="button" class="episode-card" @click="$emit('play', ep.fileId)">
            <img
              v-if="ep.coverUrl"
              class="episode-card__cover"
              :src="resolveLibraryMediaUrl(ep.coverUrl)"
              alt=""
            />
            <div v-else class="episode-card__cover episode-card__cover--empty">EP</div>
            <div class="episode-card__meta">
              <span class="episode-card__no">{{ pad(ep.episodeNumber) }}</span>
              <span v-if="ep.hasSubtitles" class="episode-card__sub" title="有字幕">字幕</span>
            </div>
            <span v-if="ep.title" class="episode-card__ep-title" :title="ep.title">
              {{ ep.title }}
            </span>
            <span class="episode-card__duration">{{ durationLabel(ep.duration) }}</span>
          </button>
          <n-dropdown
            v-if="resourceId != null"
            trigger="click"
            size="small"
            :options="cardOptions"
            @select="(key: string) => onAction(ep, key)"
          >
            <button type="button" class="episode-card__more" :disabled="busy" title="更多">⋯</button>
          </n-dropdown>
        </div>
      </div>
    </section>

    <template v-if="extras.length">
      <div class="episode-list__label">特典</div>
      <div class="episode-list__grid">
        <div v-for="extra in extras" :key="extra.fileId" class="episode-card-wrap">
          <button type="button" class="episode-card" @click="$emit('play', extra.fileId)">
            <img
              v-if="extra.coverUrl"
              class="episode-card__cover"
              :src="resolveLibraryMediaUrl(extra.coverUrl)"
              alt=""
            />
            <div v-else class="episode-card__cover episode-card__cover--empty">特典</div>
            <div class="episode-card__meta">
              <span class="episode-card__title" :title="extra.title || '特典'">
                {{ extra.title || '特典' }}
              </span>
            </div>
            <span class="episode-card__duration">{{ durationLabel(extra.duration) }}</span>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NDropdown } from 'naive-ui'
import {
  attachSubtitle,
  backfillCovers,
  updateEpisodeCover,
} from '@/infrastructure/http/seriesAssets'
import { resolveLibraryMediaUrl } from '@/infrastructure/http'
import { notify } from '@/application/notify'
import type { SeriesEpisode, SeriesExtra, SeriesSeason } from '@/domain'

const props = defineProps<{
  resourceId?: number
  seasons: SeriesSeason[]
  extras: SeriesExtra[]
}>()

const emit = defineEmits<{
  play: [fileId: number]
  refresh: []
}>()

const IMAGE_FILTER = { name: '图片', extensions: ['jpg', 'jpeg', 'png', 'webp'] }
const SUBTITLE_FILTER = { name: '字幕', extensions: ['srt', 'vtt', 'ass', 'ssa'] }

const cardOptions = [
  { label: '换封面', key: 'cover' },
  { label: '恢复默认封面', key: 'clear' },
  { label: '加字幕', key: 'subtitle' },
]

const busy = ref(false)

const episodes = computed(() => props.seasons.flatMap((season) => season.episodes ?? []))
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

/** 时长：不足一小时用 mm:ss，超过用 h:mm:ss；未知返回空串 */
function durationLabel(seconds?: number | null): string {
  if (!seconds || !Number.isFinite(seconds) || seconds <= 0) return ''
  const total = Math.round(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(rest)}`
  return `${minutes}:${pad(rest)}`
}

async function onAction(ep: SeriesEpisode, key: string): Promise<void> {
  if (props.resourceId == null || ep.id == null || busy.value) return
  busy.value = true
  try {
    if (key === 'cover') {
      const paths = (await window.electron.selectFiles([IMAGE_FILTER])) ?? []
      if (!paths[0]) return
      await updateEpisodeCover(ep.id, { imagePath: paths[0] })
      notify.toast.success('已更换该集封面')
    } else if (key === 'clear') {
      await updateEpisodeCover(ep.id, { clear: true })
      notify.toast.success('已恢复默认封面')
    } else if (key === 'subtitle') {
      const paths = (await window.electron.selectFiles([SUBTITLE_FILTER])) ?? []
      if (!paths[0]) return
      await attachSubtitle(props.resourceId, paths[0], ep.id)
      notify.toast.success('已添加字幕')
    }
    emit('refresh')
  } catch {
    notify.toast.error('操作失败')
  } finally {
    busy.value = false
  }
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
    emit('refresh')
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

.episode-card-wrap {
  position: relative;
}

.episode-card {
  position: relative;
}

.episode-card__duration {
  position: absolute;
  right: 4px;
  bottom: 2px;
  padding: 0 3px;
  border-radius: 3px;
  background: rgb(0 0 0 / 45%);
  color: #fff;
  font-size: 10px;
}

.episode-card--extra .episode-card__duration {
  position: static;
  margin-left: 6px;
  background: transparent;
  color: var(--sm-color-text-muted, #6b7280);
}
.episode-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
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

.episode-card__ep-title {
  overflow: hidden;
  max-width: 100%;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  color: var(--sm-color-text-muted, #6b7280);
}
.episode-card__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
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

.episode-card__more {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 4px;
  background: rgb(0 0 0 / 45%);
  color: #fff;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
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
