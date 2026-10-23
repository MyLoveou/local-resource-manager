<template>
  <header class="tool-bar">
    <n-input
      class="tool-bar__search"
      size="small"
      clearable
      placeholder="搜索资源、命令或 AI"
      :value="globalQ"
      @update:value="onGlobalQ"
      @keydown.enter.prevent="flushGlobalQ"
    />
    <n-button size="small" type="primary" @click="wizardRef?.open()">导入</n-button>
    <n-dropdown
      v-if="showCluster && !isTrash"
      trigger="click"
      :options="organizeOptions"
      @select="onOrganizeSelect"
    >
      <n-button size="small">整理</n-button>
    </n-dropdown>
    <n-dropdown trigger="click" :options="aiOptions" @select="onAISelect">
      <n-button size="small">AI</n-button>
    </n-dropdown>
    <n-dropdown trigger="click" :options="settingsOptions" @select="onSettingsSelect">
      <n-button size="small">设置</n-button>
    </n-dropdown>
    <div class="tool-bar__spacer" />
    <div v-if="showCluster && batchMode" class="tool-bar__batch">
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
        <n-button v-else size="tiny" :disabled="busy" @click="enter">批量选择</n-button>
        <n-button v-if="!isTrash" size="tiny" :disabled="busy" @click="enterScrape">获取元数据</n-button>
      </template>
      <template v-else>
        <span>已选 {{ selectedCount }}</span>
        <span class="tool-bar__batch-hint">Ctrl/Shift 多选 · Esc 退出</span>
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
        <n-dropdown
          v-if="!isTrash"
          trigger="click"
          :options="batchOrganizeOptions"
          @select="onOrganizeSelect"
        >
          <n-button size="tiny" :disabled="busy || selectedCount === 0">整理</n-button>
        </n-dropdown>
        <template v-if="!isTrash">
          <n-input
            class="tool-bar__tag-input"
            size="tiny"
            placeholder="打标：输入标签回车"
            :value="tagDraft"
            :disabled="busy || selectedCount === 0"
            @update:value="(value: string) => (tagDraft = value)"
            @keydown.enter.prevent="addTagDraft"
          />
          <span v-if="tagNames.length > 0" class="tool-bar__tag-chips">{{ tagNames.join(' / ') }}</span>
          <n-button
            size="tiny"
            :disabled="busy || selectedCount === 0 || tagNames.length === 0"
            @click="commitBatchTag"
          >
            打标
          </n-button>
        </template>
        <n-button size="tiny" :disabled="busy" @click="exit">退出</n-button>
      </template>
    </div>
    <n-button text class="tool-bar__ai-status" @click="router.push('/ai')">
      {{ aiStatusLabel }}
    </n-button>
    <ImportWizard ref="wizardRef" />
    <SettingsModal v-model:show="settingsOpen" :tab="settingsTab" />
    <ScrapeConfirmQueue v-model:show="scrapeOpen" :resource-ids="scrapeIds" />
    <n-modal
      v-model:show="batchCollectionOpen"
      preset="card"
      title="加入合集"
      style="width: 380px"
      :mask-closable="!batchCollectionBusy"
      :close-on-esc="!batchCollectionBusy"
    >
      <div class="tool-bar__collection-form">
        <n-select
          v-model:value="batchCollectionId"
          :options="batchCollectionOptions"
          placeholder="选择已有合集"
          filterable
          :disabled="batchCollectionBusy"
          @update:value="batchCollectionTitle = ''"
        />
        <n-input
          v-model:value="batchCollectionTitle"
          placeholder="或输入新合集名称"
          :disabled="batchCollectionBusy"
          @update:value="batchCollectionId = null"
          @keydown.enter.prevent="confirmBatchCollection"
        />
        <p class="tool-bar__collection-hint">
          将把已选 {{ selectedCount }} 项加入合集；资源仍保留在主库。
        </p>
      </div>
      <template #footer>
        <div class="tool-bar__collection-actions">
          <n-button size="small" :disabled="batchCollectionBusy" @click="batchCollectionOpen = false">
            取消
          </n-button>
          <n-button
            size="small"
            type="primary"
            :loading="batchCollectionBusy"
            :disabled="batchCollectionBusy || (!batchCollectionId && !batchCollectionTitle.trim())"
            @click="confirmBatchCollection"
          >
            确定
          </n-button>
        </div>
      </template>
    </n-modal>
    <n-modal
      v-model:show="batchCategoryOpen"
      preset="card"
      title="设置分类"
      style="width: 400px"
      :mask-closable="!batchCategoryBusy"
    >
      <div class="tool-bar__collection-form">
        <n-select
          v-model:value="batchCategoryIds"
          multiple
          filterable
          clearable
          placeholder="选择分类（可多选）"
          :options="batchCategoryOptions"
          :disabled="batchCategoryBusy"
        />
        <p class="tool-bar__collection-hint">追加不会清空已有分类；移除只移除勾选的分类。</p>
      </div>
      <template #footer>
        <div class="tool-bar__collection-actions">
          <n-button size="small" :disabled="batchCategoryBusy" @click="batchCategoryOpen = false">
            取消
          </n-button>
          <n-button
            size="small"
            type="error"
            ghost
            :loading="batchCategoryBusy"
            :disabled="batchCategoryBusy || batchCategoryIds.length === 0"
            @click="confirmBatchCategories('remove')"
          >
            移除
          </n-button>
          <n-button
            size="small"
            type="primary"
            :loading="batchCategoryBusy"
            :disabled="batchCategoryBusy || batchCategoryIds.length === 0"
            @click="confirmBatchCategories('add')"
          >
            追加
          </n-button>
        </div>
      </template>
    </n-modal>
    <n-modal
      v-model:show="batchCharacterOpen"
      preset="card"
      title="设置角色"
      style="width: 420px"
      :mask-closable="!batchCharacterBusy"
    >
      <n-select
        v-model:value="batchCharacterIds"
        multiple
        filterable
        clearable
        placeholder="选择角色（AND）"
        :options="batchCharacterOptions"
        :disabled="batchCharacterBusy"
      />
      <template #footer>
        <div class="tool-bar__collection-actions">
          <n-button size="small" :disabled="batchCharacterBusy" @click="batchCharacterOpen = false">
            取消
          </n-button>
          <n-button
            size="small"
            type="primary"
            :loading="batchCharacterBusy"
            :disabled="batchCharacterBusy || batchCharacterIds.length === 0"
            @click="confirmBatchCharacters"
          >
            加入角色
          </n-button>
        </div>
      </template>
    </n-modal>
    <n-modal
      v-model:show="batchPersonOpen"
      preset="card"
      title="设置扮演者"
      style="width: 420px"
      :mask-closable="!batchPersonBusy"
    >
      <n-select
        v-model:value="batchPersonIds"
        multiple
        filterable
        clearable
        placeholder="选择扮演者（AND）"
        :options="batchPersonOptions"
        :disabled="batchPersonBusy"
      />
      <template #footer>
        <div class="tool-bar__collection-actions">
          <n-button size="small" :disabled="batchPersonBusy" @click="batchPersonOpen = false">
            取消
          </n-button>
          <n-button
            size="small"
            type="primary"
            :loading="batchPersonBusy"
            :disabled="batchPersonBusy || batchPersonIds.length === 0"
            @click="confirmBatchPersons"
          >
            加入扮演者
          </n-button>
        </div>
      </template>
    </n-modal>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NDropdown, NInput, NModal, NPopconfirm, NSelect, type DropdownOption } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { notify } from '@/application/notify'
import ImportWizard from '@/components/ImportWizard/index.vue'
import SettingsModal from '@/components/SettingsModal/index.vue'
import ScrapeConfirmQueue from '@/components/ScrapeConfirmQueue/index.vue'
import { useShellBatchStore } from '@/application/stores/shellBatch'
import { useThemeStore } from '@/application/stores/theme'
import { useUpdateStore } from '@/application/stores/update'
import { useAIStore } from '@/application/stores/ai'
import { useBrowseQueryStore } from '@/application/stores/browseQuery'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { useCategoryTreeStore } from '@/application/stores/categoryTree'
import { getCategoryTree, getResource, listCharacters, listPersons } from '@/infrastructure/http'
import { flattenCategoryTree } from '@/domain'
import { addCollectionItems, createCollection, listCollections } from '@/infrastructure/http/collections'
import type { CategoryNode, Collection, ResourceType } from '@/domain'

const wizardRef = ref<{ open: () => void } | null>(null)
const theme = useThemeStore()
const update = useUpdateStore()
const ai = useAIStore()
const shellBatch = useShellBatchStore()
const selection = useSelectionStore()
const library = useLibraryStore()
const categoryStore = useCategoryTreeStore()
const browse = useBrowseQueryStore()
const scrapeOpen = ref(false)
const scrapeIds = ref<number[]>([])
const settingsOpen = ref(false)
const settingsTab = ref('scrape')
const route = useRoute()
const router = useRouter()
const globalQ = ref(String(route.query.q ?? ''))
let globalTimer: ReturnType<typeof setTimeout> | undefined
const { showCluster, batchMode, total, busy, selectedCount, context } = storeToRefs(shellBatch)
const { enter, exit, emptyTrash, runBatch } = shellBatch

const isTrash = computed(() => context.value === 'trash')
const aiStatusLabel = computed(() => {
  if (ai.jobActive) return 'AI 处理中'
  if (!ai.modelInstalled) return 'AI 未启用'
  if (!ai.status?.dependencyReady) return 'AI 依赖缺失'
  return ai.indexed > 0 ? 'AI 就绪' : 'AI 待索引'
})
const organizeOptions = computed<DropdownOption[]>(() => [
  { label: '批量选择', key: 'select' },
  { label: '加入合集', key: 'collections', disabled: selectedCount.value === 0 },
  { label: '设置分类', key: 'categories', disabled: selectedCount.value === 0 },
  { label: '设置角色', key: 'characters', disabled: selectedCount.value === 0 },
  { label: '设置扮演者', key: 'persons', disabled: selectedCount.value === 0 },
  { label: '获取元数据', key: 'scrape', disabled: selectedCount.value === 0 },
])

const batchOrganizeOptions = computed<DropdownOption[]>(() =>
  organizeOptions.value.filter((option) => option.key !== 'select'),
)

const aiOptions: DropdownOption[] = [
  { label: 'AI 中心', key: 'ai-center' },
  { label: '智能搜图', key: 'ai-search' },
  { label: '模型管理', key: 'ai-models' },
  { label: 'AI 任务', key: 'ai-jobs' },
  { label: 'AI 建议', key: 'ai-suggestions' },
]

function onOrganizeSelect(key: string): void {
  if (key === 'select') enter()
  else if (key === 'collections') void openBatchCollections()
  else if (key === 'categories') void openBatchCategories()
  else if (key === 'characters') void openBatchCharacters()
  else if (key === 'persons') void openBatchPersons()
  else if (key === 'scrape') void startScrape()
}

function onAISelect(key: string): void {
  if (key === 'ai-center') void router.push('/ai')
  else if (key === 'ai-search') void router.push({ path: '/ai', query: { tab: 'search' } })
  else if (key === 'ai-models') void router.push({ path: '/ai', query: { tab: 'models' } })
  else if (key === 'ai-jobs') void router.push({ path: '/ai', query: { tab: 'jobs' } })
  else if (key === 'ai-suggestions') void router.push({ path: '/ai', query: { tab: 'suggestions' } })
}

function enterScrape(): void {
  enter()
}

const tagNames = ref<string[]>([])
const tagDraft = ref('')

function addTagDraft(): void {
  const name = tagDraft.value.trim()
  if (!name) return
  if (!tagNames.value.includes(name)) tagNames.value.push(name)
  tagDraft.value = ''
}

async function commitBatchTag(): Promise<void> {
  if (tagNames.value.length === 0) return
  const names = [...tagNames.value]
  const ok = await runBatch('add_tags', names)
  if (ok) tagNames.value = []
}

const batchCollectionOpen = ref(false)
const batchCollectionBusy = ref(false)
const batchCollections = ref<Collection[]>([])
const batchCollectionId = ref<number | null>(null)
const batchCollectionTitle = ref('')
const batchCollectionOptions = computed(() =>
  batchCollections.value.map((collection) => ({
    label: `${collection.title}（${collection.memberCount}）`,
    value: collection.id,
  })),
)

async function openBatchCollections(): Promise<void> {
  if (selectedCount.value === 0) return
  batchCollectionOpen.value = true
  batchCollectionId.value = null
  batchCollectionTitle.value = ''
  batchCollectionBusy.value = false
  try {
    batchCollections.value = await listCollections()
  } catch (error) {
    notify.fromError(error, { context: '读取合集' })
  }
}

async function confirmBatchCollection(): Promise<void> {
  const ids = [...selection.selectedIds]
  if (ids.length === 0) return
  const title = batchCollectionTitle.value.trim()
  if (!title && batchCollectionId.value == null) return
  batchCollectionBusy.value = true
  try {
    let targetId = batchCollectionId.value
    let targetTitle =
      batchCollections.value.find((collection) => collection.id === targetId)?.title ?? ''
    if (title) {
      const created = await createCollection({ title })
      targetId = created.id ?? null
      targetTitle = created.title
    }
    if (targetId == null) return

    let added = 0
    let skipped = 0
    let missing = 0
    for (let index = 0; index < ids.length; index += 200) {
      const result = await addCollectionItems(targetId, ids.slice(index, index + 200))
      added += result.added
      skipped += result.skipped
      missing += result.missing
    }

    shellBatch.exit()
    library.invalidate({ collections: true, resources: true, home: true })
    const extras = [
      skipped > 0 ? `跳过重复 ${skipped} 项` : '',
      missing > 0 ? `跳过缺失 ${missing} 项` : '',
    ].filter(Boolean)
    const summary = `已加入 ${added} 项到「${targetTitle || '合集'}」${extras.length ? `（${extras.join('，')}）` : ''}`
    shellBatch.message = summary
    notify.toast.success(summary)
    batchCollectionOpen.value = false
  } catch (error) {
    notify.fromError(error, { context: '加入合集' })
  } finally {
    batchCollectionBusy.value = false
  }
}

watch(
  () => batchMode.value,
  (value) => {
    if (!value) {
      tagNames.value = []
      tagDraft.value = ''
    }
  }
)

const batchCategoryOpen = ref(false)
const batchCategoryBusy = ref(false)
const batchCategoryIds = ref<number[]>([])
const batchCategoryTree = ref<CategoryNode[]>([])
const batchCategoryType = computed(() => (route.params.type as ResourceType) || 'image')
const batchCategoryOptions = computed(() =>
  flattenCategoryTree(batchCategoryTree.value).map((node) => ({
    label: node.name,
    value: node.id,
  })),
)

async function openBatchCategories(): Promise<void> {
  if (selectedCount.value === 0) return
  batchCategoryOpen.value = true
  batchCategoryIds.value = []
  batchCategoryBusy.value = false
  try {
    batchCategoryTree.value = await categoryStore.load(batchCategoryType.value)
  } catch (error) {
    notify.fromError(error, { context: '读取分类' })
  }
}

async function confirmBatchCategories(mode: 'add' | 'remove'): Promise<void> {
  if (batchCategoryIds.value.length === 0) return
  batchCategoryBusy.value = true
  try {
    const ok = await shellBatch.runBatch(
      mode === 'add' ? 'add_categories' : 'remove_categories',
      undefined,
      [...batchCategoryIds.value],
    )
    if (!ok) {
      notify.toast.error(
        `分类${mode === 'add' ? '追加' : '移除'}未完全成功，请查看批量提示后重试`,
      )
      return
    }
    batchCategoryOpen.value = false
  } finally {
    batchCategoryBusy.value = false
  }
}

const batchCharacterOpen = ref(false)
const batchCharacterBusy = ref(false)
const batchCharacterIds = ref<number[]>([])
const batchCharacterOptions = ref<{ label: string; value: number }[]>([])

async function openBatchCharacters(): Promise<void> {
  if (selectedCount.value === 0) return
  batchCharacterOpen.value = true
  batchCharacterIds.value = []
  batchCharacterBusy.value = false
  try {
    const characters = await listCharacters()
    batchCharacterOptions.value = characters.map((character) => ({
      label: character.workName ? `${character.name} · ${character.workName}` : character.name,
      value: character.id,
    }))
  } catch (error) {
    notify.fromError(error, { context: '读取角色' })
  }
}

async function confirmBatchCharacters(): Promise<void> {
  if (batchCharacterIds.value.length === 0) return
  batchCharacterBusy.value = true
  try {
    const ok = await shellBatch.runBatch(
      'add_characters',
      undefined,
      undefined,
      [...batchCharacterIds.value],
    )
    if (!ok) {
      notify.toast.error('设置角色未完全成功，请查看批量提示')
      return
    }
    batchCharacterOpen.value = false
  } finally {
    batchCharacterBusy.value = false
  }
}

const batchPersonOpen = ref(false)
const batchPersonBusy = ref(false)
const batchPersonIds = ref<number[]>([])
const batchPersonOptions = ref<{ label: string; value: number }[]>([])

async function openBatchPersons(): Promise<void> {
  if (selectedCount.value === 0) return
  batchPersonOpen.value = true
  batchPersonIds.value = []
  batchPersonBusy.value = false
  try {
    batchPersonOptions.value = (await listPersons()).map((person) => ({
      label: person.name,
      value: person.id,
    }))
  } catch (error) {
    notify.fromError(error, { context: '读取扮演者' })
  }
}

async function confirmBatchPersons(): Promise<void> {
  if (batchPersonIds.value.length === 0) return
  batchPersonBusy.value = true
  try {
    const ok = await shellBatch.runBatch(
      'add_persons',
      undefined,
      undefined,
      undefined,
      [...batchPersonIds.value],
    )
    if (!ok) {
      notify.toast.error('设置扮演者未完全成功，请查看批量提示')
      return
    }
    batchPersonOpen.value = false
  } finally {
    batchPersonBusy.value = false
  }
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
    notify.toast.warning('所选没有视频或番剧')
    return
  }
  if (scrapeable.length < ids.length) {
    notify.toast.info(`已跳过 ${ids.length - scrapeable.length} 项非视频/番剧`)
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

const settingsOptions: DropdownOption[] = [
  { label: '设置', key: 'settings' },
  { label: '主题', key: 'theme', children: themeOptions },
  { label: '检查更新', key: 'update' },
]

function onSettingsSelect(key: string): void {
  if (key === 'settings') openSettings()
  else if (key === 'update') {
    openSettings('update')
    void update
      .check()
      .then(() => {
        if (update.status.phase === 'unsupported') {
          notify.toast.warning(update.status.message || '当前版本不支持自动更新，请手动下载')
        }
      })
      .catch((error) => notify.fromError(error, { context: '检查更新' }))
  } else void onThemeSelect(key)
}

function openSettings(name = 'scrape'): void {
  settingsTab.value = name
  settingsOpen.value = true
}

function onOpenSettings(event: Event): void {
  const name = (event as CustomEvent<string>).detail
  openSettings(name === 'consume' || name === 'update' ? name : 'scrape')
}

onMounted(() => {
  void ai.refresh()
  window.addEventListener('sm:open-settings', onOpenSettings)
  const warning = theme.consumeHydrateWarning()
  if (warning) notify.toast.warning(warning)
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
    if (error) notify.fromError(new Error(error), { context: '应用主题' })
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

.tool-bar__ai-status {
  flex-shrink: 0;
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.tool-bar__batch {
  position: fixed;
  left: 50%;
  bottom: 16px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
  max-width: calc(100vw - 40px);
  overflow-x: auto;
  padding: 8px 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--sm-color-bg-surface) 94%, transparent);
  box-shadow: var(--sm-shadow-card, 0 8px 24px rgba(0, 0, 0, 0.18));
  transform: translateX(-50%);
  font-size: 13px;
  color: var(--sm-color-text);
}

.tool-bar__tag-input {
  width: 160px;
}

.tool-bar__batch-hint {
  color: var(--sm-color-text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.tool-bar__tag-chips {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  opacity: 0.8;
}

.tool-bar__collection-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-bar__collection-hint {
  margin: 0;
  font-size: 12px;
  opacity: 0.7;
}

.tool-bar__collection-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
