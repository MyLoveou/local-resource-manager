<template>
  <aside class="category-panel" :class="{ 'category-panel--collapsed': collapsed }">
    <div class="category-panel__head">
      <button type="button" class="category-panel__title" @click="collapsed = !collapsed">
        <span>分类</span>
        <span class="category-panel__chevron">{{ collapsed ? '▸' : '▾' }}</span>
      </button>
      <button
        v-if="!collapsed"
        type="button"
        class="category-panel__manage"
        title="管理分类"
        @click="$emit('manage')"
      >
        管理
      </button>
    </div>
    <div v-if="!collapsed" class="category-panel__body">
      <button
        type="button"
        class="category-panel__all"
        :class="{ 'category-panel__all--active': selectedId === null && !uncategorized }"
        @click="select(null, false)"
      >
        全部
      </button>
      <button
        type="button"
        class="category-panel__all"
        :class="{ 'category-panel__all--active': uncategorized }"
        @click="select(null, true)"
      >
        未分类
      </button>
      <div v-if="nodes.length === 0" class="category-panel__empty">还没有分类</div>
      <n-tree
        v-else
        block-line
        selectable
        :data="treeData"
        :selected-keys="selectedId === null ? [] : [selectedId]"
        :expanded-keys="expandedKeys"
        :render-label="renderLabel"
        @update:expanded-keys="(keys: Array<string | number>) => (expandedKeys = keys)"
        @update:selected-keys="(keys: Array<string | number>) => onSelect(keys)"
      />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { NTree, type TreeOption } from 'naive-ui'
import type { CategoryNode } from '@/domain'

const props = defineProps<{
  nodes: CategoryNode[]
  selectedId: number | null
  uncategorized: boolean
}>()
const emit = defineEmits<{
  select: [id: number | null, uncategorized: boolean]
  manage: []
  createChild: [id: number]
}>()

const collapsed = ref(false)
const expandedKeys = ref<Array<string | number>>([])

const treeData = computed<TreeOption[]>(() => props.nodes.map(toOption))

function toOption(node: CategoryNode): TreeOption {
  return {
    key: node.id,
    label: node.name,
    children: node.children?.map(toOption),
  }
}

function renderLabel({ option }: { option: TreeOption }): ReturnType<typeof h> {
  const node = findNode(props.nodes, Number(option.key))
  return h('span', { class: 'category-panel__label' }, [
    h('span', { class: 'category-panel__name' }, String(option.label ?? '')),
    h('span', { class: 'category-panel__count' }, String(node?.count ?? 0)),
    h('button', {
      class: 'category-panel__plus',
      type: 'button',
      title: '添加子分类',
      onClick: (event: MouseEvent) => {
        event.stopPropagation()
        emit('createChild', Number(option.key))
      },
    }, '+'),
  ])
}

function findNode(nodes: CategoryNode[], id: number): CategoryNode | null {
  for (const node of nodes) {
    if (node.id === id) return node
    const hit = findNode(node.children ?? [], id)
    if (hit) return hit
  }
  return null
}

function onSelect(keys: Array<string | number>): void {
  const key = keys[0]
  if (key === undefined) {
    select(null, false)
    return
  }
  select(Number(key), false)
}

function select(id: number | null, uncategorized: boolean): void {
  emit('select', id, uncategorized)
}

watch(
  () => props.nodes,
  (nodes) => {
    if (expandedKeys.value.length === 0) {
      expandedKeys.value = nodes.map((node) => node.id)
    }
  },
  { immediate: true },
)
</script>

<style scoped lang="less">
.category-panel {
  width: 220px;
  flex: 0 0 220px;
  border-right: 1px solid var(--sm-color-border);
  background: var(--sm-color-bg-surface);
  overflow: auto;
  padding: 8px;

  &--collapsed {
    width: 48px;
    flex-basis: 48px;
    padding: 8px 4px;
  }
}

.category-panel__head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.category-panel__title {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: 0;
  padding: 4px;
  color: var(--sm-color-text);
  font-weight: 600;
  cursor: pointer;
}

.category-panel__chevron {
  font-size: 12px;
  opacity: 0.6;
}

.category-panel__manage {
  border: 0;
  background: transparent;
  color: var(--sm-color-text-muted);
  font-size: 12px;
  cursor: pointer;
}

.category-panel__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-panel__all {
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--sm-color-text);
  text-align: left;
  padding: 5px 8px;
  font-size: 13px;
  cursor: pointer;

  &--active {
    background: var(--sm-color-bg-muted);
    font-weight: 600;
  }
}

.category-panel__empty {
  padding: 8px;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

:deep(.category-panel__label) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}

:deep(.category-panel__name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.category-panel__count) {
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

:deep(.category-panel__plus) {
  border: 0;
  background: transparent;
  color: var(--sm-color-text-muted);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
  opacity: 0;
}

:deep(.n-tree-node:hover .category-panel__plus),
:deep(.n-tree-node--selected .category-panel__plus) {
  opacity: 1;
}
</style>
