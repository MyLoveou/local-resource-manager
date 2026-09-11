<template>
  <aside class="info-panel">
    <div v-if="resource" class="info-panel-content">
      <img v-if="resource.coverPath" :src="resource.coverPath" alt="" />
      <div class="info-panel-title">{{ resource.title }}</div>
      <div class="info-panel-rating">
        <n-rate :value="resource.rating ?? 0" :readonly="true" />
      </div>
      <div class="info-panel-type">{{ resource.type }}</div>
      <div class="info-panel-description">{{ resource.description }}</div>
      <div class="info-panel-actions">
        <button type="button" :disabled="busy" @click="handleDelete">删除</button>
      </div>
    </div>
    <div v-else class="info-panel-empty">未选择资源</div>
  </aside>
</template>

<script setup lang="ts">
import { NRate } from 'naive-ui'
import { ref, watch } from 'vue'
import { getResource } from '@/infrastructure/http'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { useSelectionStore } from '@/application/stores/selection'
import type { Resource } from '@/domain'

const selection = useSelectionStore()
const { removeResource } = useResourceHandle()
const resource = ref<Resource | null>(null)
const busy = ref(false)

watch(
  () => selection.selectedId,
  async (id) => {
    if (id == null) {
      resource.value = null
      return
    }
    try {
      resource.value = await getResource(id)
    } catch (error) {
      console.error(error)
      resource.value = null
    }
  },
  { immediate: true }
)

async function handleDelete(): Promise<void> {
  const id = selection.selectedId
  if (id == null || busy.value) return
  busy.value = true
  try {
    await removeResource(id)
    selection.clear()
  } catch (error) {
    console.error(error)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="less">
.info-panel {
  width: 350px;
  height: 100%;
  flex-shrink: 0;
  overflow: auto;
  box-sizing: border-box;
}

.info-panel-empty {
  padding: 16px;
  color: #6b7280;
}
</style>
