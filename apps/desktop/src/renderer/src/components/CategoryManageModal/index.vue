<template>
  <n-modal
    :show="show"
    preset="card"
    title="管理分类"
    style="width: 440px"
    :mask-closable="false"
    @update:show="(value: boolean) => $emit('update:show', value)"
  >
    <div class="category-manage">
      <n-select
        :value="selectedId ?? 0"
        :options="nodeOptions"
        placeholder="选择要编辑的分类，或新建"
        @update:value="selectNode"
      />
      <n-button size="small" secondary @click="startCreate">新建根分类</n-button>
      <n-input v-model:value="name" placeholder="分类名称" />
      <n-select
        :value="parentValue"
        :options="parentOptions"
        placeholder="父分类"
        @update:value="(value: number) => (parentValue = value)"
      />
      <n-input-number v-model:value="sort" :min="0" placeholder="排序" />
      <div class="category-manage__actions">
        <n-popconfirm
          v-if="selectedId !== null"
          positive-text="删除"
          negative-text="取消"
          @positive-click="remove"
        >
          <template #trigger>
            <n-button size="small" type="error" ghost>删除</n-button>
          </template>
          只允许删除没有子分类、没有资源的分类。
        </n-popconfirm>
        <span class="category-manage__spacer" />
        <n-button size="small" :disabled="!name.trim()" type="primary" :loading="busy" @click="save">
          {{ selectedId === null ? '创建' : '保存' }}
        </n-button>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NInput, NInputNumber, NModal, NPopconfirm, NSelect } from 'naive-ui'
import { notify } from '@/application/notify'
import { useCategoryTreeStore } from '@/application/stores/categoryTree'
import { useLibraryStore } from '@/application/stores/library'
import type { CategoryNode, ResourceType } from '@/domain'

const props = defineProps<{
  show: boolean
  type: ResourceType
  nodes: CategoryNode[]
  initialParentId?: number | null
}>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()

const store = useCategoryTreeStore()
const library = useLibraryStore()
const selectedId = ref<number | null>(null)
const name = ref('')
const parentValue = ref(0)
const sort = ref(0)
const busy = ref(false)

watch(
  () => props.show,
  (show) => {
    if (!show) return
    if (props.initialParentId != null) {
      selectedId.value = null
      name.value = ''
      parentValue.value = props.initialParentId
      sort.value = 0
    } else {
      startCreate()
    }
  },
  { immediate: true },
)

const flatOptions = computed(() => flattenWithPath(props.nodes))
const nodeOptions = computed(() => [
  { label: '新建分类', value: 0 },
  ...flatOptions.value.map((item) => ({ label: item.path, value: item.node.id })),
])
const parentOptions = computed(() => [
  { label: '根分类', value: 0 },
  ...flatOptions.value
    .filter((item) => item.node.id !== selectedId.value)
    .map((item) => ({ label: item.path, value: item.node.id })),
])

function flattenWithPath(
  nodes: CategoryNode[],
  prefix = '',
): { node: CategoryNode; path: string }[] {
  const out: { node: CategoryNode; path: string }[] = []
  for (const node of nodes) {
    const path = prefix ? `${prefix} / ${node.name}` : node.name
    out.push({ node, path })
    out.push(...flattenWithPath(node.children ?? [], path))
  }
  return out
}

function selectNode(value: number): void {
  if (value === 0) {
    startCreate()
    return
  }
  const node = flatOptions.value.find((item) => item.node.id === value)?.node
  if (!node) return
  selectedId.value = node.id
  name.value = node.name
  parentValue.value = node.parentId ?? 0
  sort.value = node.sort
}

function startCreate(): void {
  selectedId.value = null
  name.value = ''
  parentValue.value = 0
  sort.value = 0
}

async function save(): Promise<void> {
  if (!name.value.trim()) return
  busy.value = true
  try {
    if (selectedId.value === null) {
      await store.create(props.type, {
        name: name.value.trim(),
        parentId: parentValue.value || null,
        sort: sort.value,
      })
      notify.toast.success('分类已创建')
    } else {
      await store.update(selectedId.value, props.type, {
        name: name.value.trim(),
        parentId: parentValue.value || null,
        sort: sort.value,
      })
      notify.toast.success('分类已保存')
    }
  } catch (error) {
    notify.fromError(error, { context: '保存分类' })
  } finally {
    busy.value = false
  }
}

async function remove(): Promise<void> {
  if (selectedId.value === null) return
  busy.value = true
  try {
    await store.remove(selectedId.value, props.type)
    library.invalidate({ savedViews: true })
    startCreate()
    notify.toast.success('分类已删除')
  } catch (error) {
    notify.fromError(error, { context: '删除分类' })
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="less">
.category-manage {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.category-manage__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-manage__spacer {
  flex: 1;
}
</style>
