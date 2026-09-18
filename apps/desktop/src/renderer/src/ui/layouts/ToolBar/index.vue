<template>
  <header class="tool-bar">
    <n-button size="small" type="primary" @click="wizardRef?.open()">导入</n-button>
    <div class="tool-bar__spacer" />
    <div v-if="showCluster" class="tool-bar__batch">
      <template v-if="!batchMode">
        <span v-if="isTrash">回收站 {{ total }} 项</span>
        <n-popconfirm v-if="isTrash" positive-text="清空" negative-text="取消" @positive-click="emptyTrash">
          <template #trigger>
            <n-button size="tiny" type="error" ghost :disabled="busy">清空回收站</n-button>
          </template>
          彻底删除回收站内全部条目，不可恢复。只删除库内副本，不删除你电脑上的原文件。
        </n-popconfirm>
        <n-button v-if="isTrash" size="tiny" :disabled="busy" @click="enter">
          批量选择
        </n-button>
        <n-button v-else size="tiny" :disabled="busy" @click="enter">批量删除</n-button>
      </template>
      <template v-else>
        <span>已选 {{ selectedCount }}</span>
        <template v-if="isTrash">
          <n-popconfirm positive-text="恢复" negative-text="取消" :disabled="selectedCount === 0"
            @positive-click="() => runBatch('restore')">
            <template #trigger>
              <n-button size="tiny" :disabled="busy || selectedCount === 0">恢复</n-button>
            </template>
            确定恢复所选资源？
          </n-popconfirm>
          <n-popconfirm positive-text="彻底删除" negative-text="取消" :disabled="selectedCount === 0"
            @positive-click="() => runBatch('purge')">
            <template #trigger>
              <n-button size="tiny" type="error" ghost :disabled="busy || selectedCount === 0">
                彻底删除
              </n-button>
            </template>
            彻底删除后不可恢复。只删除库内副本，不删除你电脑上的原文件。
          </n-popconfirm>
        </template>
        <n-popconfirm v-else positive-text="移入" negative-text="取消" :disabled="selectedCount === 0"
          @positive-click="() => runBatch('trash')">
          <template #trigger>
            <n-button size="tiny" type="error" ghost :disabled="busy || selectedCount === 0">
              移入回收站
            </n-button>
          </template>
          确定将所选资源移入回收站？可稍后恢复。
        </n-popconfirm>
        <n-button size="tiny" :disabled="busy" @click="exit">取消</n-button>
      </template>
    </div>
    <n-dropdown trigger="click" :options="themeOptions" @select="onThemeSelect">
      <n-button size="small">主题</n-button>
    </n-dropdown>
    <ImportWizard ref="wizardRef" />
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NDropdown, NPopconfirm, useMessage, type DropdownOption } from 'naive-ui'
import { storeToRefs } from 'pinia'
import ImportWizard from '@/components/ImportWizard/index.vue'
import { useShellBatchStore } from '@/application/stores/shellBatch'
import { useThemeStore } from '@/application/stores/theme'

const wizardRef = ref<{ open: () => void } | null>(null)
const message = useMessage()
const theme = useThemeStore()
const shellBatch = useShellBatchStore()
const { showCluster, batchMode, total, busy, selectedCount, context } = storeToRefs(shellBatch)
const { enter, exit, emptyTrash, runBatch } = shellBatch

const isTrash = computed(() => context.value === 'trash')

const themeOptions: DropdownOption[] = [
  { label: '默认', key: 'default' },
  { label: '暗色', key: 'dark' },
  { label: '从文件选择…', key: 'file' },
  { label: '恢复默认', key: 'reset' },
]

onMounted(() => {
  const warning = theme.consumeHydrateWarning()
  if (warning) message.warning(warning)
})

async function onThemeSelect(key: string): Promise<void> {
  if (key === 'default' || key === 'reset') {
    theme.applyBuiltin('default')
    return
  }
  if (key === 'dark') {
    theme.applyBuiltin('dark')
    return
  }
  if (key === 'file') {
    const error = await theme.pickFile()
    if (error) message.error(error)
  }
}
</script>

<style scoped lang="less">
.tool-bar {
  height: 40px;
  background-color: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  border-bottom: 1px solid var(--sm-color-border);
  display: flex;
  align-items: center;
  padding: 0 var(--sm-space-3);
  gap: var(--sm-space-2);
}

.tool-bar__spacer {
  flex: 1;
  min-width: 0;
}

.tool-bar__batch {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  flex-shrink: 0;
  font-size: 13px;
  color: var(--sm-color-text);
}
</style>
