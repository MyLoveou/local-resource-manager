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
      <section v-if="collections.length" class="home__section">
        <div class="home__section-head">
          <h2>我的合集</h2>
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
      <div class="overview-container">
        <div class="overview-content">
          <h2>概览</h2>
          <div class="overview-content-cards">
            <n-card v-for="item in visibleStats" :key="item.type" :title="typeMap[item.type] ?? item.type"
              class="overview-content-card" hoverable>
              {{ item.count }}
            </n-card>
          </div>
        </div>
        <div class="overview-task">
          <h2>进行中工作</h2>
          <ul v-if="activeWork.length" class="overview-list">
            <li v-for="item in activeWork" :key="item.id">
              <button type="button" class="overview-link" @click="openWork(item)">
                {{ item.title || '未命名工作目录' }}
              </button>
            </li>
          </ul>
          <p v-else class="overview-empty">暂无进行中的工作目录</p>
        </div>
        <div class="overview-current">
          <h2>最近消费</h2>
          <ul v-if="recentConsumption.length" class="overview-list">
            <li v-for="item in recentConsumption" :key="item.id">
              <button type="button" class="overview-link" @click="openConsumed(item)">
                {{ item.title || '未命名' }}
                <span class="overview-action">{{ actionLabel(item.action) }}</span>
              </button>
            </li>
          </ul>
          <p v-else class="overview-empty">还没有打开记录</p>
        </div>
      </div>
    </div>
    <EmptyGuide v-else hint="暂无资源，请先在顶栏导入" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getHome, resolveCardImageUrl } from '@/infrastructure/http'
import { consumeResource } from '@/infrastructure/consume/consumeResource'
import { NCard } from 'naive-ui'
import type { ConsumptionItem, HomeSummary, Resource, ResourceType, SavedView } from '@/domain'
import { profileFor } from '@/domain'
import { typeMap } from '@/utils/typeMap'
import { useLibraryStore } from '@/application/stores/library'
import { notify } from '@/application/notify'
import { isSectionHidden } from '@/domain/visibility'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import CollectionCard from '@/components/CollectionCard/index.vue'

const ACTION_LABEL: Record<string, string> = {
  embedded: '内嵌打开',
  system: '系统打开',
  command: '命令打开',
  workbench: '工作台',
  open: '打开',
}

/** 首页概览数据（统计 + 最近添加 + 任务 + 工作） */
const overviewData = ref<HomeSummary | null>(null)
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
    recentConsumption.value.length > 0
  )
})

function actionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action
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
  void consumeResource(item, [item.id])
}

function openLibrary(): void {
  void router.push('/library/image')
}

function openTimeline(item: SavedView): void {
  void router.push(`/timelines/${item.id}`)
}
const initOverviewData = async () => {
  try {
    overviewData.value = await getHome()
  } catch (err) {
    notify.fromError(err, { context: '获取首页概览' })
  }
}

onMounted(async () => {
  initOverviewData()
})

const library = useLibraryStore()
watch(
  () => library.homeRevision,
  () => {
    void initOverviewData()
  }
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
    .overview-content {
      padding: 20px;

      .overview-content-cards {
        display: flex;
        flex-direction: row;

        .overview-content-card {
          flex: 1;
          margin: 10px 10px 0 0;
        }
      }
    }
  }

  .overview-task,
  .overview-current {
    padding: 0 20px 12px;
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

  .overview-action,
  .overview-empty {
    color: var(--sm-color-text-muted);
    font-size: 12px;
  }
}
</style>
