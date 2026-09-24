<template>
  <header class="tool-bar">
    <n-button size="small" type="primary" @click="wizardRef?.open()">导入</n-button>
    <n-button v-if="isWork" size="small" :loading="addingWork" @click="addWorkDirectory">添加工作目录</n-button>
    <n-button size="small" @click="downloadOpen = true">下载</n-button>
    <n-button size="small" @click="openSettings()">设置</n-button>
    <n-input
      class="tool-bar__search"
      size="small"
      clearable
      placeholder="全库搜索"
      :value="globalQ"
      @update:value="onGlobalQ"
      @keydown.enter.prevent="flushGlobalQ"
    />
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
        <n-button v-if="!isTrash" size="tiny" :disabled="busy" @click="enterScrape">获取元数据</n-button>
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
        <n-button v-if="!isTrash" size="tiny" :disabled="busy || selectedCount === 0" @click="startScrape">
          获取元数据
        </n-button>
        <n-button size="tiny" :disabled="busy" @click="exit">取消</n-button>
      </template>
    </div>
    <n-dropdown trigger="click" :options="themeOptions" @select="onThemeSelect">
      <n-button size="small">主题</n-button>
    </n-dropdown>
    <ImportWizard ref="wizardRef" />
    <DownloadDrawer v-model:show="downloadOpen" />
    <SettingsModal v-model:show="settingsOpen" :tab="settingsTab" />
    <ScrapeConfirmQueue v-model:show="scrapeOpen" :resource-ids="scrapeIds" />
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NDropdown, NInput, NPopconfirm, useMessage, type DropdownOption } from 'naive-ui'
import { storeToRefs } from 'pinia'
import ImportWizard from '@/components/ImportWizard/index.vue'
import DownloadDrawer from '@/components/DownloadDrawer/index.vue'
import SettingsModal from '@/components/SettingsModal/index.vue'
import ScrapeConfirmQueue from '@/components/ScrapeConfirmQueue/index.vue'
import { useShellBatchStore } from '@/application/stores/shellBatch'
import { useThemeStore } from '@/application/stores/theme'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { getResource } from '@/infrastructure/http'
import { createWorkDirectory } from '@/infrastructure/http/workbench'

const wizardRef = ref<{ open: () => void } | null>(null)
const message = useMessage()
const theme = useThemeStore()
const shellBatch = useShellBatchStore()
const selection = useSelectionStore()
const library = useLibraryStore()
const browse = useBrowseQueryStore()
const scrapeOpen = ref(false)
const scrapeIds = ref<number[]>([])
const downloadOpen = ref(false)
const settingsOpen = ref(false)
const settingsTab = ref('scrape')
const addingWork = ref(false)
const route = useRoute()
const router = useRouter()
const globalQ = ref(String(route.query.q ?? ''))
let globalTimer: ReturnType<typeof setTimeout> | undefined
const { showCluster, batchMode, total, busy, selectedCount, context } = storeToRefs(shellBatch)
const { enter, exit, emptyTrash, runBatch } = shellBatch

const isTrash = computed(() => context.value === 'trash')
const isWork = computed(() => route.path === '/work')

async function addWorkDirectory(): Promise<void> {
  const dir = await window.electron?.selectDirectory()
  if (!dir) return
  addingWork.value = true
  try {
    const created = await createWorkDirectory(dir)
    library.bump('work_directory')
    if (created.id != null) selection.select(created.id)
    message.success('已添加工作目录')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '添加失败')
  } finally {
    addingWork.value = false
  }
}

function enterScrape(): void {
  enter()
}

async function startScrape(): Promise<void> {
  const ids = [...selection.selectedIds]
  if (ids.length === 0) return
  const scrapeable: number[] = []
  for (const id of ids) {
    try {
      const row = await getResource(id)
      if (row.type === 'video' || row.type === 'anime') scrapeable.push(id)
    } catch {
      /* 跳过无法读取的项 */
    }
  }
  if (scrapeable.length === 0) {
    message.warning('所选没有视频或番剧')
    return
  }
  if (scrapeable.length < ids.length) {
    message.info(`已跳过 ${ids.length - scrapeable.length} 项非视频/番剧`)
  }
  scrapeIds.value = scrapeable
  scrapeOpen.value = true
}

watch(
  () => route.query.q,
  (value) => {
    if (route.path === '/search') globalQ.value = String(value ?? '')
  }
)

function goGlobalSearch(raw: string): void {
  const q = raw.trim()
  if (!q) {
    if (route.path === '/search') void router.push('/')
    return
  }
  browse.patch(undefined, undefined, { q })
  void router.push({ path: '/search', query: { q } })
}

function onGlobalQ(value: string): void {
  globalQ.value = value
  if (globalTimer) clearTimeout(globalTimer)
  globalTimer = setTimeout(() => goGlobalSearch(globalQ.value), 300)
}

function flushGlobalQ(): void {
  if (globalTimer) clearTimeout(globalTimer)
  goGlobalSearch(globalQ.value)
}

const themeOptions: DropdownOption[] = [
  { label: '默认', key: 'default' },
  { label: '暗色', key: 'dark' },
  { label: '从文件选择…', key: 'file' },
  { label: '恢复默认', key: 'reset' },
]

function openSettings(name = 'scrape'): void {
  settingsTab.value = name
  settingsOpen.value = true
}

function onOpenSettings(event: Event): void {
  const name = (event as CustomEvent<string>).detail
  openSettings(name === 'consume' ? 'consume' : 'scrape')
}

onMounted(() => {
  window.addEventListener('sm:open-settings', onOpenSettings)
  const warning = theme.consumeHydrateWarning()
  if (warning) message.warning(warning)
})

onUnmounted(() => {
  window.removeEventListener('sm:open-settings', onOpenSettings)
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

.tool-bar__search {
  width: 220px;
  flex-shrink: 0;
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
