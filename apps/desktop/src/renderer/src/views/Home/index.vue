<template>
  <div class="home">
    <div v-if="hasOverviewData">
      <div class="overview-container">
        <div class="overview-content">
          <h2>概览</h2>
          <div class="overview-content-cards">
            <n-card v-for="(count, type) in overviewData?.stats.byType" :key="type" :title="typeMap[type] ?? type"
              class="overview-content-card" hoverable>
              {{ count }}
            </n-card>
          </div>
        </div>
        <div class="overview-task"></div>
        <div class="overview-current"></div>
      </div>
    </div>
    <div v-else>
      暂无数据
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { getOverview } from '@/infrastructure/http'
import { NCard } from 'naive-ui'
import type { Overview } from '@/domain'
import { typeMap } from '@/utils/typeMap'
import { useLibraryStore } from '@/application/stores/library'

/** 首页概览数据（统计 + 最近添加 + 任务） */
const overviewData = ref<Overview | null>(null)
// 判断后端返回数据是否正常
const hasOverviewData = computed(() => {
  const byType = overviewData.value?.stats.byType
  return !!byType && Object.keys(byType).length > 0
})
const initOverviewData = async () => {
  try {
    overviewData.value = await getOverview()
    console.log(overviewData.value)
    console.log(overviewData.value?.stats.byType)
  } catch (err) {
    console.error('获取首页概览失败', err)
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
}
</style>
