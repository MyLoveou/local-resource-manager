<template>
  <div class="home">
    <div v-if="hasOverviewData">
      <section v-if="recent.length" class="home__section">
        <div class="home__section-head">
          <h2>最近添加</h2>
          <button type="button" class="home__more" @click="openLibrary">查看全部</button>
        </div>
        <div class="home__recent">
          <button
            v-for="item in recent"
            :key="item.id"
            type="button"
            class="home__recent-item"
            :title="item.title"
            @click="openRecent(item)"
          >
            <img
              v-if="item.thumbnailPath"
              :src="resolveCardImageUrl(item)"
              alt=""
              loading="lazy"
            />
            <span v-else class="home__recent-placeholder">{{ item.title }}</span>
          </button>
        </div>
      </section>

      <section v-if="resumeList.length" class="home__section">
        <div class="home__section-head">
          <h2>继续观看</h2>
        </div>
        <div class="home__resume">
          <button
            v-for="item in resumeList"
            :key="item.fileId"
            type="button"
            class="home__resume-item"
            :title="item.title"
            @click="resumePlayback(item)"
          >
            <span class="home__resume-track">
              <span class="home__resume-fill" :style="{ width: `${item.percent}%` }" />
            </span>
            <span class="home__resume-text">
              <strong>{{ item.title || '未命名' }}</strong>
              <span>{{ resumeLabel(item) }}</span>
            </span>
          </button>
        </div>
      </section>

      <section v-if="collections.length" class="home__section">
        <div class="home__section-head">
          <h2>合集</h2>
          <button type="button" class="home__more" @click="router.push('/collections')">查看全部</button>
        </div>
        <div class="home__collections">
          <CollectionCard
            v-for="item in collections"
            :key="item.id"
            :title="item.title"
            :member-count="item.memberCount"
            :previews="item.previewThumbnails ?? []"
            @open="router.push(`/collections/${item.id}`)"
          />
        </div>
      </section>

      <section v-if="savedTimelines.length" class="home__section">
        <div class="home__section-head">
          <h2>时间线</h2>
        </div>
        <div class="home__timelines">
          <button
            v-for="item in savedTimelines"
            :key="item.id"
            type="button"
            class="home__timeline"
            @click="openTimeline(item)"
          >
            {{ item.name }}
          </button>
        </div>
      </section>

      <section class="overview-container">
        <div class="overview-content">
          <div class="overview-heading">
            <h2>概览</h2>
            <span>点击卡片进入对应资源库</span>
          </div>
          <div class="overview-content-cards">
            <button
              v-for="item in visibleStats"
              :key="item.type"
              type="button"
              class="overview-stat"
              @click="openType(item.type)"
            >
              <span class="overview-stat__stack">
                <span
                  v-for="index in 3"
                  :key="index"
                  class="overview-stat__layer"
                  :class="`overview-stat__layer--${index}`"
                >
                  <img
                    v-if="previewsFor(item.type)[index - 1]"
                    :src="resolveLibraryMediaUrl(previewsFor(item.type)[index - 1])"
                    alt=""
                    loading="lazy"
                  />
                  <span v-else class="overview-stat__placeholder" />
                </span>
              </span>
              <span class="overview-stat__shade" />
              <span class="overview-stat__body">
                <strong>{{ item.count }}</strong>
                <span>{{ typeLabel(item.type) }}</span>
              </span>
            </button>
          </div>
        </div>

        <div class="overview-task">
          <div class="overview-heading">
            <h2>进行中的任务</h2>
          </div>
          <ul v-if="activeWork.length" class="overview-list">
            <li v-for="item in activeWork" :key="item.id">
              <button type="button" class="overview-link" @click="openWork(item)">
                {{ item.title || '未命名任务' }}
              </button>
            </li>
          </ul>
          <p v-else class="overview-empty">暂无进行中的任务</p>
        </div>

        <div class="overview-current">
          <div class="overview-heading">
            <h2>最近消费</h2>
          </div>
          <div v-if="recentConsumption.length" class="overview-consumption">
            <button
              v-for="item in recentConsumption"
              :key="item.id"
              type="button"
              class="overview-consume"
              :title="item.title"
              @click="openConsumed(item)"
            >
              <span class="overview-consume__cover">
                <img
                  v-if="item.thumbnailPath"
                  :src="resolveLibraryMediaUrl(item.thumbnailPath)"
                  alt=""
                  loading="lazy"
                />
                <span v-else class="overview-consume__placeholder">{{ typeLabel(item.type) }}</span>
                <span class="overview-consume__action">{{ actionLabel(item.action) }}</span>
                <span v-if="item.duration != null" class="overview-consume__duration">
                  {{ formatDuration(item.duration) }}
                </span>
              </span>
              <span class="overview-consume__meta">
                <strong>{{ item.title || '未命名资源' }}</strong>
                <span class="overview-consume__sub">
                  {{ typeLabel(item.type) }}
                  <template v-if="item.format"> · {{ item.format }}</template>
                </span>
                <span class="overview-consume__time">{{ formatDateTime(item.createdAt) }}</span>
              </span>
            </button>
          </div>
          <p v-else class="overview-empty">还没有消费记录</p>
        </div>
      </section>
    </div>
    <EmptyGuide v-else hint="还没有资源，先导入一些内容吧。" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getHome, getResumeList, resolveCardImageUrl, resolveLibraryMediaUrl } from '@/infrastructure/http'
import type { ResumeItem } from '@/domain/progress'
import { openResource } from '@/infrastructure/consume/consumeResource'
import type { ConsumptionItem, HomeSummary, Resource, ResourceType, SavedView } from '@/domain'
import { profileFor } from '@/domain'
import { typeMap } from '@/utils/typeMap'
import { useLibraryStore } from '@/application/stores/library'
import { notify } from '@/application/notify'
import { isSectionHidden } from '@/domain/visibility'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import CollectionCard from '@/components/CollectionCard/index.vue'

const ACTION_LABEL: Record<string, string> = {
  embedded: '内嵌播放',
  system: '系统打开',
  command: '命令打开',
  workbench: '工作台',
  open: '打开',
}

const overviewData = ref<HomeSummary | null>(null)
const resumeList = ref<ResumeItem[]>([])
const router = useRouter()
const activeWork = computed(() => overviewData.value?.activeWork ?? [])
const recentConsumption = computed(() => overviewData.value?.recentConsumption ?? [])
const recent = computed(() => overviewData.value?.recent ?? [])
const collections = computed(() => overviewData.value?.collections ?? [])
const savedTimelines = computed(() => overviewData.value?.savedTimelines ?? [])
const visibleStats = computed(() =>
  Object.entries(overviewData.value?.stats.byType ?? {})
    .filter(([type]) => {
      const path = profileFor(type as ResourceType)?.routePath
      return !path || !isSectionHidden(path)
    })
    .map(([type, count]) => ({ type, count })),
)
const hasOverviewData = computed(() => {
  const data = overviewData.value
  if (!data) return false
  return (
    recent.value.length > 0 ||
    collections.value.length > 0 ||
    savedTimelines.value.length > 0 ||
    visibleStats.value.some((item) => item.count > 0) ||
    activeWork.value.length > 0 ||
    recentConsumption.value.length > 0 ||
    resumeList.value.length > 0
  )
})

function typeLabel(type: string): string {
  return typeMap[type as ResourceType] ?? type
}

function previewsFor(type: string): string[] {
  return overviewData.value?.stats.previewsByType?.[type] ?? []
}

function actionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action
}

function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

function formatDateTime(value?: string | null): string {
  return value ? value.replace('T', ' ').slice(0, 16) : ''
}

function openType(type: string): void {
  const profile = profileFor(type as ResourceType)
  void router.push(profile?.routePath ?? `/library/${type}`)
}

function openWork(item: Resource): void {
  if (item.id == null) return
  void router.push({ path: '/work', query: { select: String(item.id) } })
}

function openConsumed(item: ConsumptionItem): void {
  const path = item.type === 'work_directory' ? '/work' : `/library/${item.type}`
  void router.push({ path, query: { select: String(item.resourceId) } })
}

function openRecent(item: Resource): void {
  if (item.id == null) return
  void openResource(item, { playlist: [item.id] })
}

function resumeLabel(item: ResumeItem): string {
  const parts: string[] = []
  if (item.seasonNumber) parts.push(`第 ${item.seasonNumber} 季`)
  if (item.episodeNumber) parts.push(`第 ${item.episodeNumber} 集`)
  const remain = item.duration ? Math.max(0, Math.round(item.duration - item.position)) : 0
  parts.push(remain > 0 ? `剩余 ${formatDuration(remain)}` : `${Math.round(item.percent)}%`)
  return parts.join(' · ')
}

function resumePlayback(item: ResumeItem): void {
  void openResource(
    { id: item.resourceId, type: item.type as ResourceType },
    { playlist: [item.resourceId], fileId: item.fileId },
  )
}

function openLibrary(): void {
  void router.push('/library/image')
}

function openTimeline(item: SavedView): void {
  void router.push(`/timelines/${item.id}`)
}

const initOverviewData = async (): Promise<void> => {
  try {
    overviewData.value = await getHome()
  } catch (err) {
    notify.fromError(err, { context: '读取首页数据失败' })
  }
  try {
    resumeList.value = (await getResumeList(8)).items
  } catch {
    resumeList.value = []
  }
}

onMounted(() => {
  void initOverviewData()
})

const library = useLibraryStore()
watch(
  () => library.homeRevision,
  () => {
    void initOverviewData()
  },
)
</script>

<style scoped lang="less">
.home {
  height: 100%;
  overflow: auto;

  .home__section {
    padding: 12px 20px 0;
  }

  .home__section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;

    h2 {
      font-size: 15px;
      margin: 0;
    }
  }

  .home__more {
    border: 0;
    background: transparent;
    color: var(--sm-color-text-muted);
    font-size: 12px;
    cursor: pointer;
  }

  .home__resume {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
  }

  .home__resume-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    border: 1px solid var(--sm-color-border);
    border-radius: 8px;
    background: var(--sm-color-bg-surface);
    text-align: left;
    cursor: pointer;

    &:hover {
      border-color: var(--sm-color-primary);
    }
  }

  .home__resume-track {
    position: relative;
    height: 3px;
    border-radius: 999px;
    background: var(--sm-color-border);
    overflow: hidden;
  }

  .home__resume-fill {
    position: absolute;
    inset: 0 auto 0 0;
    background: var(--sm-color-primary);
  }

  .home__resume-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 12px;

    strong {
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      color: var(--sm-color-text-muted);
    }
  }

  .home__recent {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 120px;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .home__recent-item {
    border: 0;
    padding: 0;
    border-radius: 8px;
    overflow: hidden;
    aspect-ratio: 4 / 3;
    background: var(--sm-color-bg-muted, #f1f1f1);
    cursor: pointer;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .home__recent-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 6px;
    font-size: 11px;
    color: var(--sm-color-text-muted);
  }

  .home__collections {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
  }

  .home__timelines {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .home__timeline {
    border: 1px solid var(--sm-color-border);
    border-radius: 999px;
    background: transparent;
    color: var(--sm-color-text);
    padding: 5px 12px;
    font-size: 12px;
    cursor: pointer;
  }

  .overview-container {
    padding: 0 20px 24px;
  }

  .overview-heading {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin: 20px 0 10px;

    h2 {
      margin: 0;
      font-size: 15px;
    }

    span {
      color: var(--sm-color-text-muted);
      font-size: 11px;
    }
  }

  .overview-content-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
  }

  .overview-stat {
    position: relative;
    aspect-ratio: 4 / 3;
    overflow: hidden;
    padding: 0;
    border: 1px solid var(--sm-color-border);
    border-radius: 12px;
    background: var(--sm-color-bg-muted, #f1f1f1);
    cursor: pointer;
    isolation: isolate;
    text-align: left;
    transition: transform 180ms ease, box-shadow 180ms ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 24px rgb(0 0 0 / 12%);
    }

    &:focus-visible {
      outline: 2px solid var(--sm-color-accent, #2563eb);
      outline-offset: 2px;
    }
  }

  .overview-stat__stack {
    position: absolute;
    inset: 8%;
  }

  .overview-stat__layer {
    position: absolute;
    inset: 0;
    overflow: hidden;
    border-radius: 8px;
    background: var(--sm-color-bg-surface);
    box-shadow: 0 8px 18px rgb(0 0 0 / 18%);

    &--1 {
      z-index: 3;
    }
    &--2 {
      z-index: 2;
      transform: translate(5%, 4%) rotate(3deg) scale(0.985);
    }
    &--3 {
      z-index: 1;
      transform: translate(10%, 8%) rotate(5deg) scale(0.97);
    }

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .overview-stat__placeholder {
    display: block;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #dbeafe, #f8fafc);
  }

  .overview-stat__shade {
    position: absolute;
    inset: 55% 0 0;
    z-index: 4;
    background: linear-gradient(transparent, rgb(0 0 0 / 58%));
  }

  .overview-stat__body {
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 10px;
    z-index: 5;
    display: flex;
    align-items: baseline;
    gap: 7px;
    color: #fff;
    text-shadow: 0 1px 4px rgb(0 0 0 / 45%);

    strong {
      font-size: 22px;
      line-height: 1;
    }

    span {
      font-size: 12px;
      opacity: 0.9;
    }
  }

  .overview-task,
  .overview-current {
    padding-bottom: 4px;
  }

  .overview-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .overview-link {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    padding: 8px 0;
    border: 0;
    background: transparent;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }

  .overview-consumption {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 8px;
  }

  .overview-consume {
    display: flex;
    gap: 10px;
    min-width: 0;
    padding: 8px;
    border: 1px solid var(--sm-color-border);
    border-radius: 10px;
    background: var(--sm-color-bg-surface);
    color: var(--sm-color-text);
    cursor: pointer;
    text-align: left;

    &:hover {
      background: color-mix(in srgb, var(--sm-color-primary) 5%, var(--sm-color-bg-surface));
    }
  }

  .overview-consume__cover {
    position: relative;
    flex: 0 0 82px;
    width: 82px;
    height: 62px;
    overflow: hidden;
    border-radius: 7px;
    background: var(--sm-color-bg-muted, #f1f1f1);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .overview-consume__placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    padding: 4px;
    color: var(--sm-color-text-muted);
    font-size: 10px;
    text-align: center;
  }

  .overview-consume__action,
  .overview-consume__duration {
    position: absolute;
    padding: 2px 4px;
    border-radius: 4px;
    background: rgb(0 0 0 / 62%);
    color: #fff;
    font-size: 9px;
    line-height: 1.2;
  }

  .overview-consume__action {
    left: 4px;
    top: 4px;
  }

  .overview-consume__duration {
    right: 4px;
    bottom: 4px;
  }

  .overview-consume__meta {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;

    strong {
      overflow: hidden;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .overview-consume__sub,
  .overview-consume__time,
  .overview-empty {
    color: var(--sm-color-text-muted);
    font-size: 11px;
  }

  .overview-consume__time {
    margin-top: auto;
  }
}
</style>
