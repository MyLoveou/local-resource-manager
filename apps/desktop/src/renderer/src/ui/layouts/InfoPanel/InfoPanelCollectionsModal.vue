<template>
  <n-modal
    :show="show"
    preset="card"
    title="加入合集"
    style="width: 360px"
    :mask-closable="!busy"
    :close-on-esc="!busy"
    @update:show="emit('update:show', $event)"
  >
    <p class="info-panel-collection-hint">
      勾选后保存；不会创建重复关系。
    </p>
    <div
      v-for="collection in collections"
      :key="collection.id"
      class="info-panel-collection-row"
    >
      <n-checkbox
        :checked="memberIds.has(collection.id)"
        :disabled="busy"
        @update:checked="(checked: boolean) => toggle(collection.id, checked)"
      >
        {{ collection.title }}（{{ collection.memberCount }}）
      </n-checkbox>
    </div>
    <div class="info-panel-collection-add">
      <n-input
        v-model:value="newTitle"
        size="small"
        placeholder="新合集名称"
        :disabled="busy"
        @keydown.enter.prevent="createAndAdd"
      />
      <n-button
        size="small"
        type="primary"
        :disabled="!newTitle.trim() || busy"
        @click="createAndAdd"
      >
        新建并加入
      </n-button>
    </div>
    <template #footer>
      <div class="info-panel-collection-actions">
        <n-button size="small" :disabled="busy" @click="emit('update:show', false)">
          取消
        </n-button>
        <n-button size="small" type="primary" :loading="busy" @click="save">
          保存
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NCheckbox, NInput, NModal } from 'naive-ui'
import { notify } from '@/application/notify'
import { useLibraryStore } from '@/application/stores/library'
import {
  addCollectionItem,
  createCollection,
  listCollections,
  removeCollectionItem,
  resourceCollections,
} from '@/infrastructure/http/collections'
import type { Collection } from '@/domain'

const props = defineProps<{
  show: boolean
  resourceId: number | null
}>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()

const library = useLibraryStore()
const collections = ref<Collection[]>([])
const originalIds = ref(new Set<number>())
const memberIds = ref(new Set<number>())
const newTitle = ref('')
const busy = ref(false)

async function load(): Promise<void> {
  const id = props.resourceId
  if (id == null) return
  try {
    const [all, mine] = await Promise.all([listCollections(), resourceCollections(id)])
    collections.value = all
    const ids = mine.map((collection) => collection.id)
    originalIds.value = new Set(ids)
    memberIds.value = new Set(ids)
  } catch (error) {
    notify.fromError(error, { context: '读取合集失败' })
  }
}

watch(
  () => [props.show, props.resourceId] as const,
  ([show]) => {
    if (show) void load()
  },
  { immediate: true },
)

function toggle(collectionId: number, checked: boolean): void {
  if (busy.value) return
  const next = new Set(memberIds.value)
  if (checked) next.add(collectionId)
  else next.delete(collectionId)
  memberIds.value = next
}

async function save(): Promise<void> {
  const id = props.resourceId
  if (id == null) return
  const toAdd = [...memberIds.value].filter((collectionId) => !originalIds.value.has(collectionId))
  const toRemove = [...originalIds.value].filter((collectionId) => !memberIds.value.has(collectionId))
  if (toAdd.length === 0 && toRemove.length === 0) {
    emit('update:show', false)
    return
  }
  busy.value = true
  try {
    for (const collectionId of toAdd) await addCollectionItem(collectionId, id)
    for (const collectionId of toRemove) await removeCollectionItem(collectionId, id)
    emit('update:show', false)
    library.invalidate({ collections: true, resources: true, home: true })
    notify.toast.success('合集已更新')
  } catch (error) {
    notify.fromError(error, { context: '保存合集失败' })
  } finally {
    busy.value = false
  }
}

async function createAndAdd(): Promise<void> {
  const id = props.resourceId
  const title = newTitle.value.trim()
  if (id == null || !title) return
  busy.value = true
  try {
    const created = await createCollection({ title })
    await addCollectionItem(created.id, id)
    newTitle.value = ''
    collections.value = await listCollections()
    originalIds.value = new Set([...originalIds.value, created.id])
    memberIds.value = new Set([...memberIds.value, created.id])
    library.invalidate({ collections: true, resources: true, home: true })
  } catch (error) {
    notify.fromError(error, { context: '新建合集失败' })
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="less">
.info-panel-collection-hint {
  margin: 0 0 10px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.info-panel-collection-row {
  padding: 5px 0;
}

.info-panel-collection-add {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.info-panel-collection-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
