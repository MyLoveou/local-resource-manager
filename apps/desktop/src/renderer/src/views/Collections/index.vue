<template>
  <div class="collections">
    <div class="collections__head">
      <h2 class="collections__title">
        合集
      </h2>
      <n-input
        v-model:value="newTitle"
        size="small"
        placeholder="新合集名称"
        class="collections__input"
        @keydown.enter.prevent="submit"
      />
      <n-button
        size="small"
        type="primary"
        :disabled="!newTitle.trim() || busy"
        @click="submit"
      >
        新建
      </n-button>
      <span class="collections__spacer" />
      <n-checkbox
        size="small"
        :checked="viewOptions.includeCollected"
        @update:checked="(checked: boolean) => viewOptions.setIncludeCollected(checked)"
      >
        主库显示合集内资源
      </n-checkbox>
    </div>
    <div
      v-if="!collections.length && !loading"
      class="collections__empty"
    >
      还没有合集。输入名称新建一个，把已有资源收成一组。
    </div>
    <div class="collections__grid">
      <CollectionCard
        v-for="collection in collections"
        :key="collection.id"
        :title="collection.title"
        :member-count="collection.memberCount"
        :previews="collection.previewThumbnails ?? []"
        @open="open(collection.id)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCheckbox, NInput } from 'naive-ui'
import { notify } from '@/application/notify'
import { createCollection, listCollections } from '@/infrastructure/http/collections'
import CollectionCard from '@/components/CollectionCard/index.vue'
import type { Collection } from '@/domain'
import { useViewOptionsStore } from '@/application/stores/viewOptions'

const router = useRouter()
const collections = ref<Collection[]>([])
const viewOptions = useViewOptionsStore()
const newTitle = ref('')
const loading = ref(false)
const busy = ref(false)

async function load(): Promise<void> {
  loading.value = true
  try {
    collections.value = await listCollections()
  } catch (error) {
    notify.fromError(error, { context: '读取合集' })
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  const title = newTitle.value.trim()
  if (!title) return
  busy.value = true
  try {
    const created = await createCollection({ title })
    newTitle.value = ''
    await load()
    await router.push(`/collections/${created.id}`)
  } catch (error) {
    notify.fromError(error, { context: '新建合集' })
  } finally {
    busy.value = false
  }
}

function open(id: number): void {
  void router.push(`/collections/${id}`)
}

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.collections {
  height: 100%;
  overflow: auto;
  padding: var(--sm-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--sm-space-3);
}

.collections__head {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
}

.collections__title {
  font-size: 16px;
  margin: 0;
}

.collections__input {
  width: 240px;
}

.collections__spacer {
  flex: 1;
}

.collections__empty {
  color: var(--sm-color-text-muted);
  font-size: 13px;
  margin-top: var(--sm-space-3);
}

.collections__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--sm-space-2);
}
</style>
