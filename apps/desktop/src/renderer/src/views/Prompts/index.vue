<template>
  <div class="prompts">
    <header class="prompts__bar">
      <n-select
        v-model:value="model"
        class="prompts__model"
        size="small"
        :options="modelOptions"
      />
      <n-input
        v-model:value="search"
        size="small"
        placeholder="搜索标签（中文 / 英文 / 拼音）"
        clearable
        class="prompts__search"
      />
      <n-button size="small" :disabled="!positive" @click="copyOutput">复制</n-button>
      <n-button size="small" type="primary" :disabled="!selected.length" @click="saveOpen = true">
        保存
      </n-button>
      <n-button size="small" :disabled="!selected.length" @click="clearAll">清空</n-button>
    </header>

    <div class="prompts__body">
      <aside class="prompts__cats">
        <button
          v-for="item in categories"
          :key="item.id"
          type="button"
          :class="['prompts__cat', { 'is-active': item.id === category }]"
          @click="category = item.id"
        >
          <span>{{ item.icon }} {{ item.name }}</span>
          <span class="prompts__count">{{ item.tags.length }}</span>
        </button>
      </aside>

      <main class="prompts__tags">
        <div class="prompts__tag-grid">
          <button
            v-for="tag in visibleTags"
            :key="tag.en"
            type="button"
            :class="['prompts__tag', { 'is-picked': picked.has(tag.en) }]"
            :title="tag.en"
            @click="toggle(tag)"
          >
            {{ tag.zh || tag.en }}
          </button>
        </div>
        <p v-if="!visibleTags.length" class="prompts__hint">没有匹配的标签</p>
      </main>

      <aside class="prompts__output">
        <div class="prompts__label">正面（{{ selected.length }}）</div>
        <ul v-if="selected.length" class="prompts__picked">
          <li v-for="(item, index) in selected" :key="item.en">
            <span class="prompts__picked-name" :title="item.en">{{ item.zh || item.en }}</span>
            <button type="button" class="prompts__step" @click="bump(index, -0.1)">−</button>
            <span class="prompts__weight">{{ item.weight.toFixed(1) }}</span>
            <button type="button" class="prompts__step" @click="bump(index, 0.1)">+</button>
            <button type="button" class="prompts__step" @click="remove(index)">×</button>
          </li>
        </ul>
        <p v-else class="prompts__hint">从中间选标签</p>

        <div class="prompts__label">输出</div>
        <textarea class="prompts__text" :value="positive" readonly rows="6" />
        <div class="prompts__label">负面</div>
        <textarea v-model="negative" class="prompts__text" rows="3" />

        <div class="prompts__label">最近存档</div>
        <ul class="prompts__saves">
          <li v-for="item in saves" :key="item.id">
            <button type="button" class="prompts__save-load" @click="loadSave(item)">
              {{ item.title }}
            </button>
            <button type="button" class="prompts__step" @click="removeSave(item.id)">×</button>
          </li>
        </ul>
        <p v-if="!saves.length" class="prompts__hint">还没有存档</p>
      </aside>
    </div>

    <n-modal v-model:show="saveOpen" preset="card" title="保存提示词" style="width: 420px">
      <n-input v-model:value="saveTitle" placeholder="给这条提示词起个名字" />
      <p class="prompts__hint">{{ selected.length }} 个标签 · 模型 {{ model }}</p>
      <div class="prompts__actions">
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
  listPromptSaves,
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
const selected = ref<Picked[]>([])
const negative = ref('')
const saves = ref<PromptSave[]>([])
const saveOpen = ref(false)
const saveTitle = ref('')
const saving = ref(false)

const categories = computed(() => library.value?.categories ?? [])
const modelOptions = computed(() =>
  Object.entries(library.value?.models ?? {}).map(([value, item]) => ({
    label: item.name || value,
    value,
  })),
)
const picked = computed(() => new Set(selected.value.map((item) => item.en)))
const prefix = computed(() => library.value?.models?.[model.value]?.prefix ?? '')

const visibleTags = computed(() => {
  const list = categories.value.find((item) => item.id === category.value)?.tags ?? []
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return list.slice(0, 400)
  return list
    .filter((tag) => {
      const zh = (tag.zh || '').toLowerCase()
      const en = tag.en.toLowerCase()
      if (en.includes(keyword) || zh.includes(keyword)) return true
      return (pinyinOf(zh) || '').startsWith(keyword)
    })
    .slice(0, 200)
})

const positive = computed(() => {
  const body = selected.value
    .map((item) => (item.weight === 1 ? item.en : `(${item.en}:${item.weight.toFixed(1)})`))
    .join(', ')
  const head = prefix.value.trim()
  if (!head) return body
  return body ? `${head}, ${body}` : head
})

function pinyinOf(zh: string): string {
  const dict = library.value?.pinyin ?? {}
  let out = ''
  for (const char of zh) out += dict[char]?.split(',')[0] ?? char
  return out
}

function toggle(tag: { en: string; zh: string }): void {
  const index = selected.value.findIndex((item) => item.en === tag.en)
  if (index >= 0) selected.value.splice(index, 1)
  else selected.value.push({ en: tag.en, zh: tag.zh, weight: 1 })
}

function bump(index: number, delta: number): void {
  const item = selected.value[index]
  if (!item) return
  item.weight = Math.min(2, Math.max(0.5, Number((item.weight + delta).toFixed(1))))
}

function remove(index: number): void {
  selected.value.splice(index, 1)
}

function clearAll(): void {
  selected.value = []
  negative.value = ''
}

async function copyOutput(): Promise<void> {
  try {
    await navigator.clipboard.writeText(positive.value)
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
      tags: selected.value.map((item) => item.en),
      params: library.value?.models?.[model.value]?.params as Record<string, unknown> | undefined,
    })
    notify.toast.success('已保存')
    saveOpen.value = false
    saveTitle.value = ''
    await loadSaves()
  } catch {
    notify.toast.error('保存失败')
  } finally {
    saving.value = false
  }
}

function loadSave(item: PromptSave): void {
  model.value = item.model
  negative.value = item.negative
  const names = item.positive
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
  selected.value = names.map((en) => ({ en, zh: '', weight: 1 }))
}

async function removeSave(id: number): Promise<void> {
  await deletePromptSave(id)
  await loadSaves()
}

onMounted(async () => {
  try {
    library.value = await getPromptLibrary()
    category.value = library.value.categories[0]?.id ?? ''
  } catch {
    notify.toast.error('内置库加载失败')
  }
  await loadSaves()
})
</script>

<style scoped lang="less">
.prompts {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 8px;
  padding: 12px;
}

.prompts__bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prompts__model {
  width: 130px;
}

.prompts__search {
  flex: 1;
  max-width: 340px;
}

.prompts__body {
  display: flex;
  gap: 10px;
  min-height: 0;
  flex: 1;
}

.prompts__cats {
  width: 150px;
  flex-shrink: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.prompts__cat {
  display: flex;
  justify-content: space-between;
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.prompts__cat.is-active {
  background: var(--sm-color-bg-muted, #eee);
  font-weight: 600;
}

.prompts__count {
  color: var(--sm-color-text-muted, #9ca3af);
}

.prompts__tags {
  flex: 1;
  min-width: 0;
  overflow: auto;
}

.prompts__tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.prompts__tag {
  border: 1px solid var(--sm-color-border);
  background: transparent;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  color: inherit;
  cursor: pointer;
}

.prompts__tag.is-picked {
  border-color: var(--sm-color-primary, #2080f0);
  color: var(--sm-color-primary, #2080f0);
}

.prompts__output {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
}

.prompts__label {
  font-size: 12px;
  font-weight: 600;
}

.prompts__picked,
.prompts__saves {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.prompts__picked li,
.prompts__saves li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.prompts__picked-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompts__step {
  border: 1px solid var(--sm-color-border);
  background: transparent;
  border-radius: 4px;
  width: 18px;
  height: 18px;
  line-height: 1;
  font-size: 12px;
  cursor: pointer;
  color: inherit;
}

.prompts__weight {
  width: 26px;
  text-align: center;
  color: var(--sm-color-text-muted, #6b7280);
}

.prompts__text {
  width: 100%;
  border: 1px solid var(--sm-color-border);
  border-radius: 6px;
  padding: 6px;
  font-size: 12px;
  font-family: inherit;
  resize: vertical;
  background: transparent;
  color: inherit;
}

.prompts__save-load {
  flex: 1;
  min-width: 0;
  text-align: left;
  border: none;
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: inherit;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompts__hint {
  margin: 0;
  font-size: 12px;
  color: var(--sm-color-text-muted, #9ca3af);
}

.prompts__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}
</style>
