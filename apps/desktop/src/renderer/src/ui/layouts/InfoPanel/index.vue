<template>
  <aside class="info-panel">
    <div v-if="resource" class="info-panel-content">
      <img v-if="resource.coverPath" :src="resource.coverPath" alt="封面" />
      <div class="info-panel-title">{{ resource.title }}</div>
      <div class="info-panel-rating">
        <n-rate :value="resource.rating ?? 0" readonly />
      </div>
      <div class="info-panel-type">{{ resource.type }}</div>
      <div v-if="resource.description" class="info-panel-description">
        {{ resource.description }}
      </div>
      <div class="info-panel-actions">
        <button type="button" @click="handleDelete" :disabled="deleting">删除</button>
        <p v-if="errorMessage" class="info-panel-error">{{ errorMessage }}</p>
      </div>
    </div>
    <div v-else class="info-panel-empty">未选择资源</div>
  </aside>
</template>

<script setup lang="ts">
import { NRate } from 'naive-ui'
import { ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { getResource } from '@/infrastructure/http'
import { useSelectionStore } from '@/application/stores/selection'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import type { Resource } from '@/domain'

const selection = useSelectionStore()
const { selectedId } = storeToRefs(selection)
const { removeResource } = useResourceHandle()

const resource = ref<Resource | null>(null)
const deleting = ref(false)
const errorMessage = ref('')

watch(
  selectedId,
  async (id) => {
    errorMessage.value = ''
    if (id === null) {
      resource.value = null
      return
    }
    try {
      resource.value = await getResource(id)
    } catch (error) {
      resource.value = null
      errorMessage.value = '加载详情失败'
      console.error(error)
    }
  },
  { immediate: true }
)

async function handleDelete(): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  deleting.value = true
  errorMessage.value = ''
  try {
    await removeResource(id)
    selection.clear()
  } catch (error) {
    errorMessage.value = '删除失败'
    console.error(error)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped lang="less">
.info-panel {
  width: 350px;
  height: 100%;
  min-height: 0;
  overflow: auto;
  box-sizing: border-box;
  border-left: 1px solid #e5e7eb;
  padding: 12px;
}

.info-panel-empty {
  color: #6b7280;
}

.info-panel-title {
  font-weight: 600;
  margin: 8px 0;
}

.info-panel-error {
  color: #b91c1c;
  margin: 8px 0 0;
}

.info-panel-actions button {
  margin-top: 12px;
}
</style>
