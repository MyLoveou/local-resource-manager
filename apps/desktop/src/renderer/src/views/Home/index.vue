<template>
  <div class="home">
    <div v-if="hasOverviewData">
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
import { getOverview } from '@/infrastructure/http'
import { NCard } from 'naive-ui'
import type { ConsumptionItem, Overview, Resource, ResourceType } from '@/domain'
import { profileFor } from '@/domain'
import { typeMap } from '@/utils/typeMap'
import { useLibraryStore } from '@/application/stores/library'
import { notify } from '@/application/notify'
import { isSectionHidden } from '@/domain/visibility'
import EmptyGuide from '@/components/EmptyGuide/index.vue'

const ACTION_LABEL: Record<string, string> = {
  embedded: '内嵌打开',
  system: '系统打开',
  command: '命令打开',
  workbench: '工作台',
  open: '打开',
}

/** 首页概览数据（统计 + 最近添加 + 任务 + 工作） */
const overviewData = ref<Overview | null>(null)
const router = useRouter()
const activeWork = computed(() => overviewData.value?.activeWork ?? [])
const recentConsumption = computed(() => overviewData.value?.recentConsumption ?? [])
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
  const path = profileFor(item.type as ResourceType)?.routePath ?? '/'
  void router.push({ path, query: { select: String(item.resourceId) } })
}
const initOverviewData = async () => {
  try {
    overviewData.value = await getOverview()
  } catch (err) {
    notify.fromError(err, { context: '获取首页概览' })
  }
}

onMounted(async () => {
  initOverviewData()
})

const library = useLibraryStore()
watch(
  () => library.revision,
  () => {
    void initOverviewData()
  }
)
</script>

<style scoped lang="less">
.home {
  height: 100%;
  overflow: auto;

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
