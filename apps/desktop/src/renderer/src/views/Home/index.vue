<template>
  <div class="home">
    <h1>首页</h1>
    <pre>{{ overviewData }}</pre>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getOverview } from '@/infrastructure/http'
import type { Overview } from '@/domain'

/** 首页概览数据（统计 + 最近添加 + 任务） */
const overviewData = ref<Overview | null>(null)

onMounted(async () => {
  try {
    overviewData.value = await getOverview()
  } catch (err) {
    console.error('获取首页概览失败', err)
  }
})
</script>

<style scoped lang="less"></style>
