<template>
  <aside class="info-panel">
    <div class="info-panel-content" v-if="resource">
      <!-- 封面 -->
      <img :src="resource?.coverPath ?? ''" alt="封面" />
      <!-- 标题 -->
      <div class="info-panel-title">
        {{ resource?.title }}
      </div>
      <!-- 评分 -->
      <div class="info-panel-rating">
        <n-rate :value="resource?.rating ?? 0" :readonly="true" />
      </div>
      <!-- 分类 -->
      <div class="info-panel-type">
        {{ resource?.type }}
      </div>
      <!-- 标签 -->
      <div class="info-panel-tags">
        {{ resource?.tags }}
      </div>
      <!-- 描述 -->
      <div class="info-panel-description">
        {{ resource?.description }}
      </div>
      <!-- 基本数据 -->
      <div class="info-panel-basic-data">
        {{ resource?.basicData }}
      </div>
      <!-- 操作 -->
      <div class="info-panel-actions">
        <button @click="handleEdit">编辑</button>
        <button @click="handleDelete">删除</button>
      </div>
    </div>
    <div v-else>
      测试无数据
    </div>
  </aside>
</template>

<script setup lang="ts">
import { NRate } from 'naive-ui'
import { getResource } from '@/infrastructure/http'
import { onMounted, ref, watch } from 'vue'
import type { Resource } from '@/domain'
const props = defineProps({
  resourceId: {
    type: Number || undefined,
    required: true
  }
})

const resource = ref<Resource | null>(null)

const handleEdit = () => {
  console.log('编辑')
}
const handleDelete = () => {
  console.log('删除')
}
const initResource = async () => {
  try {
    resource.value = await getResource(props.resourceId)
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  initResource()
})

watch(() => props.resourceId, async () => {
  try {
    resource.value = await getResource(props.resourceId)
  } catch (error) {
    console.error(error)
  }
}, { immediate: true })
</script>

<style scoped lang="less">
// @import '@/ui/styles/variables.less';

.info-panel {
  width: 350px;
}
</style>
