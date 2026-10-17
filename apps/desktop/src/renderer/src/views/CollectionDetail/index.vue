<template>
  <div class="collection-detail">
    <div class="collection-detail__head">
      <h2 class="collection-detail__title">
        {{ collection?.title ?? '合集' }}
      </h2>
      <n-button
        size="small"
        :disabled="selectedId === null"
        @click="moveSelected('up')"
      >
        上移
      </n-button>
      <n-button
        size="small"
        :disabled="selectedId === null"
        @click="moveSelected('down')"
      >
        下移
      </n-button>
      <n-button
        size="small"
        type="error"
        ghost
        :disabled="selectedId === null"
        @click="removeSelected"
      >
        移出
      </n-button>
      <n-button
        size="small"
        :disabled="members.length === 0"
        :loading="exporting"
        @click="exportToFolder"
      >
        导出
      </n-button>
      <n-button
        size="small"
        @click="goBack"
      >
        返回
      </n-button>
    </div>
    <div
      v-if="!members.length && !loading"
      class="collection-detail__empty"
    >
      合集还没有成员。在资源的右侧信息栏里「加入合集」。
    </div>
    <VirtualGrid
      v-else
      class="collection-detail__grid"
      :items="gridItems"
      :selected-ids="selectedId !== null ? [selectedId] : []"
      @card-click="onCardClick"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { notify } from '@/application/notify'
import { resolveCardImageUrl } from '@/infrastructure/http'
import {
  collectionMembers,
  exportCollection,
  getCollection,
  moveCollectionItem,
  removeCollectionItem,
} from '@/infrastructure/http/collections'
import VirtualGrid from '@/components/VirtualGrid/index.vue'
import type { Collection, Resource } from '@/domain'
import { useSelectionStore } from '@/application/stores/selection'

const route = useRoute()
const router = useRouter()
const selection = useSelectionStore()
const collection = ref<Collection | null>(null)
const members = ref<Resource[]>([])
const loading = ref(false)
const selectedId = computed(() => selection.selectedId)

const gridItems = computed(() =>
  members.value.flatMap((item) =>
    item.id === undefined
      ? []
      : [{ id: item.id, title: item.title, coverUrl: resolveCardImageUrl(item) }],
  ),
)

async function load(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) return
  loading.value = true
  try {
    collection.value = await getCollection(id)
    members.value = await collectionMembers(id)
    loading.value = false
  } catch (error) {
    loading.value = false
    notify.fromError(error, { context: '读取合集' })
  }
}

function onCardClick(_event: MouseEvent, itemId: number): void {
  selection.select(itemId)
}

async function removeSelected(): Promise<void> {
  const id = Number(route.params.id)
  const rid = selectedId.value
  if (!Number.isFinite(id) || rid === null) return
  try {
    await removeCollectionItem(id, rid)
    selection.clear()
    await load()
  } catch (error) {
    notify.fromError(error, { context: '移出合集' })
  }
}

async function moveSelected(direction: 'up' | 'down'): Promise<void> {
  const id = Number(route.params.id)
  const rid = selectedId.value
  if (!Number.isFinite(id) || rid === null) return
  try {
    await moveCollectionItem(id, rid, direction)
    await load()
  } catch (error) {
    notify.fromError(error, { context: '调整顺序' })
  }
}

function goBack(): void {
  void router.push('/collections')
}

const exporting = ref(false)

async function exportToFolder(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) return
  const dir = await window.electron?.selectDirectory()
  if (!dir) return
  exporting.value = true
  try {
    const result = await exportCollection(id, dir)
    if (result.skipped > 0) {
      notify.toast.warning(`已导出 ${result.exported} 个文件，跳过 ${result.skipped} 个（文件缺失）`)
    } else {
      notify.toast.success(`已导出 ${result.exported} 个文件`)
    }
  } catch (error) {
    notify.fromError(error, { context: '导出合集' })
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  selection.clear()
  void load()
})
</script>

<style scoped lang="less">
.collection-detail {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: var(--sm-space-3);
}

.collection-detail__head {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  flex-shrink: 0;
  margin-bottom: var(--sm-space-2);
}

.collection-detail__title {
  font-size: 16px;
  margin: 0 var(--sm-space-2) 0 0;
}

.collection-detail__grid {
  flex: 1;
  min-height: 0;
}

.collection-detail__empty {
  color: var(--sm-color-text-muted);
  font-size: 13px;
  margin-top: var(--sm-space-3);
}
</style>
