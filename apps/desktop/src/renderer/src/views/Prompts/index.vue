<template>
  <div class="ps">
    <header class="ps__head">
      <div class="ps__head-left">
        <n-select v-model:value="model" size="small" :options="modelOptions" class="ps__model" />
        <n-input
          v-model:value="search"
          size="small"
          clearable
          placeholder="搜索标签：中文 / 英文 / 拼音"
          class="ps__search"
        />
      </div>
      <div class="ps__head-right">
        <n-button size="small" :disabled="!positive" @click="copy(positive)">复制正面</n-button>
        <n-button size="small" :disabled="!negative" @click="copy(negative)">复制负面</n-button>
        <n-button size="small" type="primary" :disabled="!positive" @click="saveOpen = true">
          保存
        </n-button>
        <span class="ps__switch"><n-switch v-model:value="showNsfw" size="small" @update:value="saveNsfw" /> 成人向</span>
        <n-button size="small" quaternary :disabled="!hasAny" @click="clearAll">清空</n-button>
      </div>
    </header>

    <div class="ps__body">
      <nav class="ps__nav">
        <button
          v-for="item in navItems"
          :key="item.id"
          type="button"
          :class="['ps__nav-item', { 'is-active': item.id === category }]"
          @click="category = item.id"
        >
          <span class="ps__nav-name">{{ item.icon }} {{ item.name }}</span>
          <span class="ps__nav-count">{{ item.count }}</span>
        </button>
      </nav>

      <section class="ps__pick">
        <div class="ps__mode">
          <button
            type="button"
            :class="['ps__mode-btn', { 'is-active': mode === 'positive' }]"
            @click="mode = 'positive'"
          >
            正向 <em>{{ pos.length }}</em>
          </button>
          <button
            type="button"
            :class="['ps__mode-btn', { 'is-active': mode === 'negative' }]"
            @click="mode = 'negative'"
          >
            负面 <em>{{ neg.length }}</em>
          </button>
          <span class="ps__mode-hint">点击标签会加入当前编辑的一侧</span>
          <n-select
            v-model:value="sortMode"
            size="tiny"
            class="ps__sort"
            :options="[
              { label: '按热度', value: 'hot' },
              { label: '按名称', value: 'name' },
            ]"
          />
        </div>

        <div class="ps__tags">
          <button
            v-for="tag in visibleTags"
            :key="tag.en"
            type="button"
            :class="['ps__tag', { 'is-on': picked.has(tag.en) }]"
            :title="tag.en"
            @click="toggle(tag)"
          >
            <span>{{ tag.zh || tag.en }}</span>
            <em v-if="tag.count" class="ps__tag-count">{{ compact(tag.count) }}</em>
          </button>
          <p v-if="!visibleTags.length" class="ps__empty">没有匹配的标签</p>
        </div>
      </section>

      <aside class="ps__side">
        <section class="ps__card">
          <div class="ps__card-head">
            <span>正面 · {{ pos.length }}</span>
            <button type="button" class="ps__link" :disabled="!pos.length" @click="pos = []">
              清空
            </button>
          </div>
          <ul v-if="pos.length" class="ps__chips">
            <li v-for="(item, index) in pos" :key="item.en" class="ps__chip">
              <span class="ps__chip-name" :title="item.en">{{ item.zh || item.en }}</span>
              <button type="button" @click="bump(pos, index, -0.1)">−</button>
              <em>{{ item.weight.toFixed(1) }}</em>
              <button type="button" @click="bump(pos, index, 0.1)">+</button>
              <button type="button" class="ps__chip-x" @click="pos.splice(index, 1)">×</button>
            </li>
          </ul>
          <p v-else class="ps__empty">从中间选标签</p>
          <textarea class="ps__out" readonly rows="4" :value="positive" />
        </section>

        <section class="ps__card">
          <div class="ps__card-head">
            <span>负面 · {{ neg.length }}</span>
            <button type="button" class="ps__link" @click="fillModelNegative">载入模型负面</button>
          </div>
          <ul v-if="neg.length" class="ps__chips">
            <li v-for="(item, index) in neg" :key="item.en" class="ps__chip">
              <span class="ps__chip-name" :title="item.en">{{ item.zh || item.en }}</span>
              <button type="button" class="ps__chip-x" @click="neg.splice(index, 1)">×</button>
            </li>
          </ul>
          <p v-else class="ps__empty">可留空，或点「载入模型负面」</p>
          <textarea class="ps__out" rows="3" :value="negative" @input="onNegativeInput" />
        </section>

        <section class="ps__card ps__card--list">
          <div class="ps__card-head">
            <span>最近存档</span>
            <button type="button" class="ps__link" @click="loadSaves">刷新</button>
          </div>
          <ul v-if="saves.length" class="ps__saves">
            <li v-for="item in saves" :key="item.id">
              <img v-if="item.image_data" class="ps__thumb" :src="item.image_data" alt="" />
              <button type="button" class="ps__save-name" :title="item.positive" @click="loadSave(item)">
                {{ item.title }}
              </button>
              <button type="button" class="ps__chip-x" @click="removeSave(item.id)">×</button>
            </li>
          </ul>
          <p v-else class="ps__empty">还没有存档</p>
        </section>
      </aside>
    </div>

    <n-modal v-model:show="saveOpen" preset="card" title="保存提示词" class="ps__modal">
      <n-input v-model:value="saveTitle" placeholder="给这条提示词起个名字" />
      <div class="ps__attach">
        <input ref="fileInput" type="file" accept="image/*" class="ps__file" @change="onPickImage" />
        <n-button size="tiny" @click="pickImage">选择风格预览图</n-button>
        <img v-if="draftImage" class="ps__preview" :src="draftImage" alt="" />
        <span class="ps__empty">{{ pos.length }} 正向 · {{ neg.length }} 负面 · {{ modelLabel }}</span>
      </div>
      <div class="ps__modal-actions">
        <n-button size="small" @click="saveOpen = false">取消</n-button>
        <n-button size="small" type="primary" :loading="saving" @click="doSave">保存</n-button>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NInput, NModal, NSelect } from 'naive-ui'
import {
  addPromptHistory,
  createPromptSave,
  deletePromptSave,
  getPromptLibrary,
  getPromptSettings,
  listPromptSaves,
  putPromptSettings,
  type PromptLibrary,
  type PromptSave,
} from '@/infrastructure/http/prompts'
import { notify } from '@/application/notify'

interface Picked {
  en: string
  zh: string
  weight: number
}

const library = ref<PromptLibrary | null>(null)
const model = ref('anima')
const category = ref('')
const search = ref('')
const mode = ref<'positive' | 'negative'>('positive')
const pos = ref<Picked[]>([])
const neg = ref<Picked[]>([])
const saves = ref<PromptSave[]>([])
const saveOpen = ref(false)
const saveTitle = ref('')
const showNsfw = ref(false)
const sortMode = ref<'hot' | 'name'>('hot')
const saving = ref(false)
const draftImage = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const categories = computed(() =>
  (library.value?.categories ?? []).filter((item) => showNsfw.value || item.id !== 'nsfw'),
)
const danbooru = computed(() => library.value?.danbooru ?? [])
const navItems = computed(() => [
  { id: 'danbooru:general', name: 'Danbooru 热门', icon: '📚', count: danbooru.value.filter((x) => x.cat === 'general').length },
  { id: 'danbooru:artist', name: 'Danbooru 画师', icon: '🎨', count: danbooru.value.filter((x) => x.cat === 'artist').length },
  { id: 'danbooru:character', name: 'Danbooru 角色', icon: '🎭', count: danbooru.value.filter((x) => x.cat === 'character').length },
  ...categories.value.map((item) => ({
    id: item.id,
    name: item.name,
    icon: item.icon,
    count: item.tags.length,
  })),
])
const modelOptions = computed(() =>
  Object.entries(library.value?.models ?? {}).map(([value, item]) => ({
    label: item.name || value,
    value,
  })),
)
const modelLabel = computed(() => library.value?.models?.[model.value]?.name ?? model.value)
const prefix = computed(() => trimEnd(library.value?.models?.[model.value]?.prefix ?? ''))
const modelNegative = computed(() => library.value?.models?.[model.value]?.negative ?? '')
const hasAny = computed(() => pos.value.length > 0 || neg.value.length > 0)
const picked = computed(
  () => new Set([...pos.value, ...neg.value].map((item) => item.en)),
)

const visibleTags = computed(() => {
  const list = currentTags.value
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return sortTags(list).slice(0, 400)
  const filtered = list.filter((tag) => {
      const zh = (tag.zh || '').toLowerCase()
      if (tag.en.toLowerCase().includes(keyword) || zh.includes(keyword)) return true
      return pinyinOf(zh).startsWith(keyword)
    })
  return sortTags(filtered).slice(0, 200)
})

function sortTags(tags: { en: string; zh: string; count: number }[]) {
  if (sortMode.value === 'name') return [...tags].sort((a, b) => a.en.localeCompare(b.en))
  return [...tags].sort((a, b) => b.count - a.count)
}

const currentTags = computed(() => {
  if (category.value.startsWith('danbooru:')) {
    const cat = category.value.split(':')[1]
    return danbooru.value
      .filter((item) => item.cat === cat && (showNsfw.value || !item.nsfw))
      .map((item) => ({ en: item.en, zh: item.zh, count: item.count }))
  }
  return (categories.value.find((item) => item.id === category.value)?.tags ?? []).map((item) => ({
    ...item,
    count: 0,
  }))
})

const positive = computed(() => compose(pos.value, prefix.value))
const negative = computed(() => compose(neg.value, ''))

function trimEnd(text: string): string {
  return text.replace(/[\s,，]+$/, '')
}

function compose(list: Picked[], head: string): string {
  const body = list
    .map((item) => (item.weight === 1 ? item.en : `(${item.en}:${item.weight.toFixed(1)})`))
    .join(', ')
  if (!head) return body
  return body ? `${head}, ${body}` : head
}

function compact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return String(value)
}

function pinyinOf(zh: string): string {
  const dict = library.value?.pinyin ?? {}
  let out = ''
  for (const char of zh) out += dict[char]?.split(',')[0] ?? char
  return out
}

function activeList(): typeof pos {
  return mode.value === 'positive' ? pos : neg
}

function toggle(tag: { en: string; zh: string }): void {
  const list = activeList()
  const index = list.value.findIndex((item) => item.en === tag.en)
  if (index >= 0) list.value.splice(index, 1)
  else list.value.push({ en: tag.en, zh: tag.zh, weight: 1 })
}

function bump(list: Picked[], index: number, delta: number): void {
  const item = list[index]
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

function onNegativeInput(event: Event): void {
  const text = (event.target as HTMLTextAreaElement).value
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

async function loadSaves(): Promise<void> {
  try {
    saves.value = await listPromptSaves({})
  } catch {
    saves.value = []
  }
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

function pickImage(): void {
  fileInput.value?.click()
}

async function onPickImage(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  draftImage.value = await shrink(file)
}

/** 缩到 384px 的 JPEG data URL，避免存档列表过大 */
function shrink(file: File, max = 384): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.onload = () => {
      const image = new Image()
      image.onerror = () => reject(new Error('解析图片失败'))
      image.onload = () => {
        const scale = Math.min(1, max / Math.max(image.width, image.height))
        const canvas = document.createElement('canvas')
        canvas.width = Math.round(image.width * scale)
        canvas.height = Math.round(image.height * scale)
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('画布不可用'))
          return
        }
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/jpeg', 0.82))
      }
      image.src = String(reader.result)
    }
    reader.readAsDataURL(file)
  })
}

function loadSave(item: PromptSave): void {
  model.value = item.model
  pos.value = item.positive
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .filter((en) => en !== prefix.value)
    .map((en) => ({ en, zh: '', weight: 1 }))
  neg.value = item.negative
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((en) => ({ en, zh: '', weight: 1 }))
}

async function removeSave(id: number): Promise<void> {
  await deletePromptSave(id)
  await loadSaves()
}

async function saveNsfw(value: boolean): Promise<void> {
  try {
    await putPromptSettings({ showNsfw: value })
  } catch {
    notify.toast.error('设置保存失败')
  }
}

onMounted(async () => {
  try {
    library.value = await getPromptLibrary()
    const settings = await getPromptSettings()
    showNsfw.value = Boolean(settings.showNsfw)
    category.value = library.value.categories[0]?.id ?? ''
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
  padding: 16px 18px;
  gap: 12px;
  background: var(--sm-color-bg, transparent);
}

.ps__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ps__head-left,
.ps__head-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ps__switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}

.ps__model {
  width: 132px;
}

.ps__search {
  width: 280px;
}

.ps__body {
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr) 360px;
  gap: 14px;
  min-height: 0;
  flex: 1;
}

.ps__nav {
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-right: 4px;
}

.ps__nav-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12.5px;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.ps__nav-item:hover {
  background: var(--sm-color-bg-muted, #f3f4f6);
}

.ps__nav-item.is-active {
  background: var(--sm-color-bg-muted, #e9edf3);
  font-weight: 600;
}

.ps__nav-count {
  font-size: 11px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.ps__pick {
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 12px;
  padding: 12px;
}

.ps__mode {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ps__mode-btn {
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 12.5px;
  color: inherit;
  cursor: pointer;
}

.ps__mode-btn.is-active {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
  background: color-mix(in srgb, var(--sm-color-primary, #2080f0) 8%, transparent);
}

.ps__mode-btn em {
  font-style: normal;
  opacity: 0.7;
  margin-left: 2px;
}

.ps__mode-hint {
  font-size: 11.5px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.ps__tags {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  overflow: auto;
  padding-right: 4px;
}

.ps__tag {
  border: 1px solid var(--sm-color-border, #e5e7eb);
  background: transparent;
  border-radius: 999px;
  padding: 3px 11px;
  font-size: 12.5px;
  color: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.ps__tag-count {
  font-style: normal;
  font-size: 10.5px;
  margin-left: 4px;
  opacity: 0.55;
}

.ps__sort {
  width: 100px;
  margin-left: auto;
}

.ps__tag:hover {
  border-color: var(--sm-color-primary, #2080f0);
}

.ps__tag.is-on {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
  background: color-mix(in srgb, var(--sm-color-primary, #2080f0) 8%, transparent);
}

.ps__side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
  min-height: 0;
}

.ps__card {
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ps__card--list {
  flex: 1;
  min-height: 120px;
}

.ps__card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12.5px;
  font-weight: 600;
}

.ps__link {
  border: none;
  background: transparent;
  color: var(--sm-color-primary, #2080f0);
  font-size: 11.5px;
  cursor: pointer;
  padding: 0;
}

.ps__link:disabled {
  color: var(--sm-color-text-muted, #cbd5e1);
  cursor: default;
}

.ps__chips {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 132px;
  overflow: auto;
}

.ps__chip {
  display: flex;
  align-items: center;
  gap: 3px;
  border: 1px solid var(--sm-color-border, #e5e7eb);
  border-radius: 999px;
  padding: 2px 6px 2px 9px;
  font-size: 11.5px;
}

.ps__chip-name {
  max-width: 130px;
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
  color: var(--sm-color-text-muted, #6b7280);
  min-width: 22px;
  text-align: center;
}

.ps__chip-x {
  opacity: 0.5;
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
  overflow: auto;
}

.ps__saves li {
  display: flex;
  align-items: center;
  gap: 4px;
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

.ps__modal {
  width: 420px;
}

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
}

.ps__thumb {
  width: 22px;
  height: 22px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.ps__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
