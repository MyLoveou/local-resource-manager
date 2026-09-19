<template>
  <div class="browse-controls">
    <n-input
      size="small"
      clearable
      :placeholder="placeholder"
      :value="localQ"
      @update:value="onQ"
      @keydown.enter.prevent="flushQ"
    />
    <n-select
      size="small"
      class="browse-controls__sort"
      :options="sortOptions"
      :value="session.sort"
      @update:value="(value: string) => patch({ sort: value })"
    />
    <n-button size="small" @click="toggleOrder">
      {{ session.order === 'desc' ? '降序' : '升序' }}
    </n-button>
    <n-select
      size="small"
      class="browse-controls__tags"
      multiple
      filterable
      clearable
      placeholder="标签"
      :options="tagOptions"
      :value="session.tagIds"
      @update:value="(value: number[]) => patch({ tagIds: value ?? [] })"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { NButton, NInput, NSelect } from 'naive-ui'
import { getTags } from '@/infrastructure/http'
import { SORT_LABELS, allowedSortKeys, type ResourceStatus, type ResourceType } from '@/domain'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'

const props = defineProps<{
  type?: ResourceType
  status?: ResourceStatus
  placeholder: string
}>()

const browse = useBrowseQueryStore()
const session = computed(() => browse.ensure(props.type, props.status))
const localQ = ref(session.value.q)
const tagOptions = ref<{ label: string; value: number }[]>([])
let timer: ReturnType<typeof setTimeout> | undefined

const sortOptions = computed(() =>
  allowedSortKeys(props.status === 'trashed' ? undefined : props.type).map((key) => ({
    label: SORT_LABELS[key] ?? key,
    value: key,
  }))
)

watch(
  () => session.value.q,
  (value) => {
    localQ.value = value
  }
)

onMounted(() => {
  void getTags().then((tags) => {
    tagOptions.value = tags.flatMap((tag) =>
      tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
    )
  })
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})

function patch(partial: { q?: string; sort?: string; order?: 'asc' | 'desc'; tagIds?: number[] }): void {
  browse.patch(props.type, props.status, partial)
}

function onQ(value: string): void {
  localQ.value = value
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    patch({ q: localQ.value })
  }, 300)
}

function flushQ(): void {
  if (timer) clearTimeout(timer)
  patch({ q: localQ.value })
}

function toggleOrder(): void {
  patch({ order: session.value.order === 'desc' ? 'asc' : 'desc' })
}
</script>

<style scoped lang="less">
.browse-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sm-space-2);
  padding: var(--sm-space-2);
  flex-shrink: 0;
}

.browse-controls__sort {
  width: 140px;
}

.browse-controls__tags {
  min-width: 160px;
  flex: 1;
}
</style>
