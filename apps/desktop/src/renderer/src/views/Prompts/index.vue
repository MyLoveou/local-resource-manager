<template>
  <div class="ps">
    <header class="ps__top">
      <n-select v-model:value="model" size="small" :options="modelOptions" class="ps__model" />
      <n-input
        v-model:value="search"
        size="small"
        clearable
        placeholder="搜索全部标签：中文 / 英文 / 拼音"
        class="ps__search"
      />
      <n-select v-model:value="sortMode" size="small" class="ps__sort" :options="sortOptions" />
      <label class="ps__nsfw">
        <n-switch v-model:value="showNsfw" size="small" @update:value="saveNsfw" />
        成人向
      </label>
      <div class="ps__spacer" />
      <n-button size="small" :disabled="!positive" @click="copy(positive)">复制正面</n-button>
      <n-button size="small" :disabled="!negative" @click="copy(negative)">复制负面</n-button>
      <n-button size="small" type="primary" :disabled="!positive" @click="saveOpen = true">
        保存
      </n-button>
      <n-button size="small" quaternary :disabled="!hasAny" @click="clearAll">清空</n-button>
      <n-dropdown trigger="click" :options="transferOptions" @select="onTransfer">
        <n-button size="small" quaternary>导入导出</n-button>
      </n-dropdown>
      <input ref="saveInput" type="file" accept="application/json,.json" class="ps__file" @change="onImportFile" />
      <input ref="libInput" type="file" accept="application/json,.json" class="ps__file" @change="onLibraryFile" />
    </header>

    <div v-if="!libraryReady" class="ps__notice">
      内置库尚未导入，当前只能使用已保存的提示词。
      <button type="button" class="ps__link" @click="libInput?.click()">导入内置库</button>
    </div>

    <div class="ps__body">
      <nav class="ps__rail">
        <template v-for="group in navGroups" :key="group.label">
          <div class="ps__group">{{ group.label }}</div>
          <button
            v-for="item in group.items"
            :key="item.id"
            type="button"
            :class="['ps__nav', { 'is-active': item.id === category }]"
            @click="selectCategory(item.id)"
          >
            <span class="ps__nav-icon">{{ item.icon }}</span>
            <span class="ps__nav-name">{{ item.name }}</span>
            <span class="ps__nav-count">{{ compact(item.count) }}</span>
          </button>
        </template>
      </nav>

      <PromptStage
        :title="stageTitle"
        :total="stageCount"
        :tags="visibleTags"
        :picked="picked"
        :selected="selectedTotal"
        :searching="!!search.trim()"
        :remaining="stageCount - visibleTags.length"
        @toggle="toggle"
        @more="limit += PAGE"
      />

      <PromptComposer
        :tab="tab"
        :items="activeList"
        :output="tab === 'positive' ? positive : negative"
        :positive-count="pos.length"
        :negative-count="neg.length"
        :saves="saves"
        @update:tab="tab = $event"
        @bump="bump"
        @remove="activeList.splice($event, 1)"
        @fill-negative="fillModelNegative"
        @write="onNegativeInput"
        @refresh-saves="loadSaves"
        @load-save="loadSave"
        @remove-save="removeSave"
      />
    </div>

    <n-modal
      v-model:show="saveOpen"
      preset="card"
      title="保存提示词"
      :style="{ width: '460px' }"
      class="ps__modal"
    >
      <n-input v-model:value="saveTitle" placeholder="给这条提示词起个名字" />
      <div class="ps__attach">
        <input ref="fileInput" type="file" accept="image/*" class="ps__file" @change="onPickImage" />
        <n-button size="tiny" @click="pickImage">选择风格预览图</n-button>
        <img v-if="draftImage" class="ps__preview" :src="draftImage" alt="" />
        <button v-if="draftImage" type="button" class="ps__preview-x" @click="draftImage = ''">×</button>
        <span class="ps__muted">{{ pos.length }} 正向 · {{ neg.length }} 负面 · {{ modelLabel }}</span>
      </div>
      <div class="ps__modal-actions">
        <n-button size="small" @click="saveOpen = false">取消</n-button>
        <n-button size="small" type="primary" :loading="saving" @click="doSave">保存</n-button>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NDropdown, NInput, NModal, NSelect, NSwitch } from 'naive-ui'
import {
  addPromptHistory,
  createPromptSave,
  deletePromptSave,
  getPromptLibrary,
  getPromptSettings,
  listPromptSaves,
  type PromptLibrary,
  type PromptSave,
} from '@/infrastructure/http/prompts'
import { notify } from '@/application/notify'
import type { StageTag } from '@/components/PromptStage/index.vue'
import { compact, compose, pinyinOf, shrinkImage, trimEnd, type PickedTag } from '@/domain/prompts/format'
import PromptComposer from '@/components/PromptComposer/index.vue'
import PromptStage from '@/components/PromptStage/index.vue'
import { persistShowNsfw } from '@/domain/prompts/settings'
import { downloadBackup, downloadLibrary, importBackup, importLibrary } from '@/domain/prompts/transfer'

interface Tag {
  key: string
  en: string
  zh: string
  count: number
  cat: string
}

const PAGE = 240
const library = ref<PromptLibrary | null>(null)
const model = ref('anima')
const category = ref('danbooru:general')
const search = ref('')
const sortMode = ref<'hot' | 'name'>('hot')
const showNsfw = ref(false)
const tab = ref<'positive' | 'negative'>('positive')
const limit = ref(PAGE)
const pos = ref<PickedTag[]>([])
const neg = ref<PickedTag[]>([])
const saves = ref<PromptSave[]>([])
const saveOpen = ref(false)
const saveTitle = ref('')
const saving = ref(false)
const draftImage = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const saveInput = ref<HTMLInputElement | null>(null)
const libInput = ref<HTMLInputElement | null>(null)

const transferOptions = [
  { label: '导出存档', key: 'export-saves' },
  { label: '导入存档', key: 'import-saves' },
  { label: '导出内置库', key: 'export-library' },
  { label: '导入内置库', key: 'import-library' },
]

const libraryReady = computed(() => {
  const lib = library.value
  if (!lib) return true
  return (lib.categories?.length ?? 0) > 0 || (lib.danbooru?.length ?? 0) > 0
})

const sortOptions = [
  { label: '按热度', value: 'hot' },
  { label: '按名称', value: 'name' },
]

const builtinCategories = computed(() =>
  (library.value?.categories ?? []).filter((item) => showNsfw.value || item.id !== 'nsfw'),
)
const danbooru = computed(() => library.value?.danbooru ?? [])
const modelOptions = computed(() =>
  Object.entries(library.value?.models ?? {}).map(([value, item]) => ({
    label: item.name || value,
    value,
  })),
)
const modelLabel = computed(() => library.value?.models?.[model.value]?.name ?? model.value)
const prefix = computed(() => trimEnd(library.value?.models?.[model.value]?.prefix ?? ''))
const modelNegative = computed(() => library.value?.models?.[model.value]?.negative ?? '')
const activeList = computed(() => (tab.value === 'positive' ? pos.value : neg.value))
const hasAny = computed(() => pos.value.length > 0 || neg.value.length > 0)
const selectedTotal = computed(() => pos.value.length + neg.value.length)
const picked = computed(() => new Set([...pos.value, ...neg.value].map((item) => item.en)))
const positive = computed(() => compose(pos.value, prefix.value))
const negative = computed(() => compose(neg.value, ''))

const navGroups = computed(() => {
  const danbooruItems = [
    { id: 'danbooru:general', name: '热门标签', icon: '📚' },
    { id: 'danbooru:artist', name: '画师', icon: '🎨' },
    { id: 'danbooru:character', name: '角色', icon: '🎭' },
    { id: 'danbooru:copyright', name: '作品', icon: '📺' },
    { id: 'danbooru:meta', name: '元信息', icon: '🏷' },
  ].map((item) => ({
    ...item,
    count: danbooru.value.filter((tag) => tag.cat === item.id.split(':')[1]).length,
  }))
  return [
    { label: 'Danbooru', items: danbooruItems },
    {
      label: '内置标签',
      items: builtinCategories.value.map((item) => ({
        id: item.id,
        name: item.name,
        icon: item.icon,
        count: item.tags.length,
      })),
    },
  ]
})

const stageTitle = computed(() => {
  if (search.value.trim()) return '搜索结果'
  for (const group of navGroups.value) {
    const found = group.items.find((item) => item.id === category.value)
    if (found) return `${found.icon} ${found.name}`
  }
  return '标签'
})

/** 当前分类或全局搜索得到的完整列表（未排序未分页） */
const allTags = computed<Tag[]>(() => {
  const keyword = search.value.trim().toLowerCase()
  if (keyword) {
    const fromBuiltin = builtinCategories.value.flatMap((categoryItem) =>
      categoryItem.tags.map((tag) => ({ key: `${categoryItem.id}:${tag.en}`, en: tag.en, zh: tag.zh, count: 0, cat: categoryItem.id })),
    )
    const fromDanbooru = danbooru.value
      .filter((tag) => showNsfw.value || !tag.nsfw)
      .map((tag) => ({ key: `danbooru:${tag.en}`, en: tag.en, zh: tag.zh, count: tag.count, cat: tag.cat }))
    return [...fromBuiltin, ...fromDanbooru].filter((tag) => {
      if (tag.en.toLowerCase().includes(keyword) || (tag.zh || '').toLowerCase().includes(keyword)) return true
      return pinyinOf(tag.zh || '', library.value?.pinyin ?? {}).startsWith(keyword)
    })
  }
  if (category.value.startsWith('danbooru:')) {
    const cat = category.value.split(':')[1]
    return danbooru.value
      .filter((tag) => tag.cat === cat && (showNsfw.value || !tag.nsfw))
      .map((tag) => ({ key: `danbooru:${tag.en}`, en: tag.en, zh: tag.zh, count: tag.count, cat: tag.cat }))
  }
  const found = builtinCategories.value.find((item) => item.id === category.value)
  return (found?.tags ?? []).map((tag) => ({
    key: `${category.value}:${tag.en}`,
    en: tag.en,
    zh: tag.zh,
    count: 0,
    cat: category.value,
  }))
})

const stagedTags = computed(() => {
  const list = [...allTags.value]
  if (sortMode.value === 'name') list.sort((a, b) => a.en.localeCompare(b.en))
  else list.sort((a, b) => b.count - a.count)
  return list
})

const stageCount = computed(() => stagedTags.value.length)
const visibleTags = computed(() => stagedTags.value.slice(0, limit.value))
const hasMore = computed(() => visibleTags.value.length < stageCount.value)

watch([category, search, sortMode, showNsfw], () => {
  limit.value = PAGE
})

function selectCategory(id: string): void {
  category.value = id
  search.value = ''
}

function toggle(tag: StageTag): void {
  const list = activeList.value
  const index = list.findIndex((item) => item.en === tag.en)
  if (index >= 0) list.splice(index, 1)
  else list.push({ en: tag.en, zh: tag.zh, weight: 1 })
}

function bump(index: number, delta: number): void {
  const item = activeList.value[index]
  if (!item) return
  item.weight = Math.min(2, Math.max(0.5, Number((item.weight + delta).toFixed(1))))
}

function fillModelNegative(): void {
  neg.value = modelNegative.value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((en) => ({ en, zh: '', weight: 1 }))
}

function onNegativeInput(text: string): void {
  neg.value = text
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((en) => ({ en, zh: '', weight: 1 }))
}

function clearAll(): void {
  pos.value = []
  neg.value = []
}

async function copy(text: string): Promise<void> {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    notify.toast.success('已复制')
    await addPromptHistory({ model: model.value, positive: positive.value, negative: negative.value })
  } catch {
    notify.toast.error('复制失败')
  }
}

function pickImage(): void {
  fileInput.value?.click()
}

async function onPickImage(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    draftImage.value = await shrinkImage(file)
  } catch {
    notify.toast.error('图片处理失败')
  }
}

async function doExport(): Promise<void> {
  const count = await downloadBackup()
  notify.toast.success(count ? `已导出 ${count} 条存档` : '当前没有存档可导出')
}

function onTransfer(key: string): void {
  if (key === 'export-saves') void doExport()
  else if (key === 'import-saves') saveInput.value?.click()
  else if (key === 'export-library') void doLibraryExport()
  else if (key === 'import-library') libInput.value?.click()
}

async function doLibraryExport(): Promise<void> {
  const count = await downloadLibrary().catch(() => -1)
  if (count < 0) notify.toast.error('内置库导出失败')
  else notify.toast.success(`已导出内置库（${count} 项）`)
}

async function onLibraryFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    notify.toast.success(await importLibrary(file))
    library.value = await getPromptLibrary()
  } catch (error) {
    const detail = error instanceof Error ? error.message : ''
    notify.toast.error(detail ? `导入失败：${detail}` : '导入失败')
  } finally {
    input.value = ''
  }
}

async function onImportFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const result = await importBackup(file)
    if (!result.saves && !result.skipped) {
      notify.toast.warning('文件里没有可导入的存档')
      return
    }
    notify.toast.success(
      `导入完成：存档 ${result.saves} · 标签 ${result.customTags} · 预设 ${result.customPresets}（跳过 ${result.skipped}）`,
    )
    await loadSaves()
  } catch (error) {
    const detail = error instanceof Error ? error.message : ''
    notify.toast.error(detail ? `导入失败：${detail}` : '导入失败')
  } finally {
    input.value = ''
  }
}

async function loadSaves(): Promise<void> {
  try {
    saves.value = await listPromptSaves({})
  } catch {
    saves.value = []
  }
}

async function saveNsfw(value: boolean): Promise<void> {
  await persistShowNsfw(value).catch(() => notify.toast.error('设置保存失败'))
}

async function doSave(): Promise<void> {
  const title = saveTitle.value.trim() || `提示词 ${new Date().toLocaleString()}`
  saving.value = true
  try {
    await createPromptSave({
      title,
      model: model.value,
      positive: positive.value,
      negative: negative.value,
      tags: pos.value.map((item) => item.en),
      image_data: draftImage.value || undefined,
    })
    notify.toast.success('已保存')
    saveOpen.value = false
    saveTitle.value = ''
    draftImage.value = ''
    await loadSaves()
  } catch (error) {
    const detail = error instanceof Error ? error.message : ''
    notify.toast.error(detail ? `保存失败：${detail}` : '保存失败')
  } finally {
    saving.value = false
  }
}

/** 解析一条已保存的提示词：去掉模型前缀、还原 (tag:1.2) 权重、去重。 */
function parsePrompt(text: string, head: string): PickedTag[] {
  let body = text.trim()
  if (head && body.startsWith(head)) {
    body = body.slice(head.length).replace(/^[\s,，]+/, '')
  }
  const seen = new Set<string>()
  const result: PickedTag[] = []
  for (const part of body.split(',')) {
    const piece = part.trim()
    if (!piece) continue
    const weighted = piece.match(/^\((.*):([\d.]+)\)$/)
    const en = weighted ? weighted[1].trim() : piece
    if (!en || seen.has(en)) continue
    seen.add(en)
    result.push({ en, zh: '', weight: weighted ? Number(weighted[2]) : 1 })
  }
  return result
}

function loadSave(item: PromptSave): void {
  model.value = item.model
  // 用该存档自己的模型前缀清理，避免把前缀当成普通标签又拼一次
  const ownPrefix = trimEnd(library.value?.models?.[item.model]?.prefix ?? '')
  pos.value = parsePrompt(item.positive, ownPrefix)
  neg.value = parsePrompt(item.negative, '')
  tab.value = 'positive'
}

async function removeSave(id: number): Promise<void> {
  await deletePromptSave(id)
  await loadSaves()
}

onMounted(async () => {
  try {
    library.value = await getPromptLibrary()
    const settings = await getPromptSettings()
    showNsfw.value = Boolean(settings.showNsfw)
  } catch {
    notify.toast.error('内置库加载失败')
  }
  await loadSaves()
})
</script>

<style scoped lang="less">
.ps {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 10px;
  padding: 14px 16px;
}

.ps__top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ps__model {
  width: 120px;
}

.ps__search {
  width: 260px;
}

.ps__sort {
  width: 100px;
}

.ps__nsfw {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}

.ps__spacer {
  flex: 1;
}

.ps__notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 8px;
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}

.ps__body {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr) 372px;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.ps__rail {
  overflow: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ps__group {
  margin: 10px 0 4px;
  padding-left: 8px;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--sm-color-text-muted, #9ca3af);
}

.ps__group:first-child {
  margin-top: 0;
}

.ps__nav {
  display: flex;
  align-items: center;
  gap: 7px;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 12.5px;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.ps__nav:hover {
  background: var(--sm-color-bg-muted, #f3f4f6);
}

.ps__nav.is-active {
  background: var(--sm-color-bg-muted, #e9edf3);
  font-weight: 600;
}

.ps__nav-icon {
  width: 16px;
}

.ps__nav-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps__nav-count {
  font-size: 11px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.ps__stage {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
}

.ps__stage-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--sm-color-border, #e5e7eb);
  font-size: 12.5px;
}

.ps__muted {
  font-size: 11.5px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.ps__tags {
  flex: 1;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
}

.ps__tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  border-radius: 8px;
  padding: 4px 9px;
  font-size: 12.5px;
  color: inherit;
  cursor: pointer;
}

.ps__tag:hover {
  border-color: var(--sm-color-primary, #2080f0);
}

.ps__tag.is-on {
  border-color: var(--sm-color-primary, #2080f0);
  background: color-mix(in srgb, var(--sm-color-primary, #2080f0) 9%, transparent);
  color: var(--sm-color-primary, #2080f0);
}

.ps__tag.is-artist .ps__tag-name::before {
  content: '@';
  opacity: 0.5;
  margin-right: 1px;
}

.ps__tag-name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps__tag-count {
  font-style: normal;
  font-size: 10.5px;
  opacity: 0.5;
}

.ps__more {
  padding: 6px 12px;
  border-top: 1px solid var(--sm-color-border, #e5e7eb);
  text-align: center;
}

.ps__composer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 12px;
  padding: 10px 12px;
  overflow: auto;
}

.ps__tabs {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ps__tab {
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  border-radius: 999px;
  padding: 3px 12px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}

.ps__tab.is-active {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
}

.ps__tab em {
  font-style: normal;
  opacity: 0.65;
  margin-left: 2px;
}

.ps__link {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--sm-color-primary, #2080f0);
  font-size: 11.5px;
  cursor: pointer;
  padding: 0;
}

.ps__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 54px;
  max-height: 150px;
  overflow: auto;
  border: 1px dashed var(--sm-color-border, #e5e7eb);
  border-radius: 8px;
  padding: 8px;
}

.ps__chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 999px;
  padding: 2px 6px 2px 9px;
  font-size: 11.5px;
}

.ps__chip-name {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps__chip button {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
  opacity: 0.7;
}

.ps__chip em {
  font-style: normal;
  min-width: 22px;
  text-align: center;
  color: var(--sm-color-text-muted, #6b7280);
}

.ps__chip-x {
  opacity: 0.45;
}

.ps__out {
  width: 100%;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 8px;
  padding: 8px;
  font-size: 12px;
  line-height: 1.55;
  font-family: inherit;
  resize: vertical;
  background: transparent;
  color: inherit;
}

.ps__empty {
  margin: 0;
  font-size: 11.5px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.ps__saves {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ps__saves li {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ps__thumb {
  width: 24px;
  height: 24px;
  object-fit: cover;
  border-radius: 5px;
  flex-shrink: 0;
}

.ps__thumb--empty {
  background: var(--sm-color-bg-muted, #f3f4f6);
}

.ps__save-name {
  flex: 1;
  min-width: 0;
  text-align: left;
  border: none;
  background: transparent;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
  padding: 3px 4px;
  border-radius: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps__save-name:hover {
  background: var(--sm-color-bg-muted, #f3f4f6);
}


</style>

<style lang="less">

.ps__attach {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.ps__file {
  display: none;
}

.ps__preview {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  flex-shrink: 0;
}

.ps__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.ps__preview-x {
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  color: inherit;
  border-radius: 999px;
  width: 20px;
  height: 20px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
}
</style>
