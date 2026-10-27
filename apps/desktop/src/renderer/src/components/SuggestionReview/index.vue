<template>
  <n-modal
    :show="show"
    preset="card"
    title="导入建议"
    style="width: 760px"
    @update:show="onShow"
  >
    <div class="review">
      <p v-if="loading" class="review__empty">加载中…</p>
      <p v-else-if="!groups.length" class="review__empty">没有待审阅的建议</p>
      <template v-else>
        <div class="review__head">
          <span class="review__count">共 {{ total }} 条 · {{ groups.length }} 组</span>
          <n-button size="tiny" quaternary @click="selectHighOnly">只选高置信</n-button>
          <n-button size="tiny" quaternary @click="selectAll">全选</n-button>
          <n-button size="tiny" quaternary @click="clearAll">全不选</n-button>
        </div>
        <ul class="review__list">
          <li
            v-for="group in groups"
            :key="groupKey(group)"
            class="review__item"
            :class="`review__item--${tier(group.confidence)}`"
          >
            <n-checkbox
              :checked="selected.has(groupKey(group))"
              @update:checked="(checked: boolean) => toggle(group, checked)"
            />
            <div class="review__body">
              <div class="review__line">
                <span class="review__value">{{ suggestionLabel(group) }}</span>
                <n-tag size="tiny" :type="tagType(group.confidence)">
                  {{ Math.round(group.confidence * 100) }}%
                </n-tag>
                <n-tag v-if="group.source === 'ai'" size="tiny" type="info">AI</n-tag>
                <span class="review__n">×{{ group.count }}</span>
              </div>
              <p v-if="group.reasons.length" class="review__reason">{{ group.reasons[0] }}</p>
            </div>
          </li>
        </ul>
      </template>
    </div>
    <template #footer>
      <div class="review__footer">
        <n-button quaternary :disabled="busy || !groups.length" @click="rejectAll">
          全部忽略
        </n-button>
        <n-button quaternary :disabled="busy || !selected.size" @click="rejectSelected">
          忽略所选
        </n-button>
        <n-button
          type="primary"
          :disabled="busy || !selected.size"
          :loading="busy"
          @click="applySelected"
        >
          采纳所选（{{ selected.size }}）
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NCheckbox, NModal, NTag } from 'naive-ui'
import { notify } from '@/application/notify'
import {
  applySuggestions,
  getSuggestionGroups,
  rejectSuggestions,
} from '@/infrastructure/http'
import {
  HIGH_CONFIDENCE,
  confidenceTier,
  groupKey,
  suggestionLabel,
  type SuggestionGroup,
  type SuggestionGroupKey,
} from '@/domain/smartImport'

const props = defineProps<{
  show: boolean
  jobId?: string | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  changed: []
}>()

const groups = ref<SuggestionGroup[]>([])
const total = ref(0)
const selected = ref(new Set<string>())
const loading = ref(false)
const busy = ref(false)

const tagType = computed(() => (confidence: number) => {
  const tier = confidenceTier(confidence)
  return tier === 'high' ? 'success' : tier === 'mid' ? 'warning' : 'default'
})

function tier(confidence: number) {
  return confidenceTier(confidence)
}

function onShow(value: boolean): void {
  emit('update:show', value)
}

function toggle(group: SuggestionGroup, checked: boolean): void {
  const key = groupKey(group)
  if (checked) selected.value.add(key)
  else selected.value.delete(key)
  selected.value = new Set(selected.value)
}

function selectHighOnly(): void {
  selected.value = new Set(
    groups.value.filter((g) => g.confidence >= HIGH_CONFIDENCE).map(groupKey),
  )
}

function selectAll(): void {
  selected.value = new Set(groups.value.map(groupKey))
}

function clearAll(): void {
  selected.value = new Set()
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const page = await getSuggestionGroups(props.jobId ?? null)
    groups.value = page.groups
    total.value = page.total
    selectHighOnly()
  } catch (err) {
    notify.fromError(err, { context: '读取导入建议失败' })
    groups.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function selectedKeys(): SuggestionGroupKey[] {
  return groups.value
    .filter((group) => selected.value.has(groupKey(group)))
    .map((group) => ({ field: group.field, value: group.value }))
}

async function applySelected(): Promise<void> {
  const payload = selectedKeys()
  if (!payload.length) return
  busy.value = true
  try {
    const result = await applySuggestions({ groups: payload })
    notify.toast.success(`已采纳 ${result.accepted} 条建议`)
    emit('changed')
    await load()
  } catch (err) {
    notify.fromError(err, { context: '采纳建议失败' })
  } finally {
    busy.value = false
  }
}

async function rejectSelected(): Promise<void> {
  const payload = selectedKeys()
  if (!payload.length) return
  busy.value = true
  try {
    const result = await rejectSuggestions({ groups: payload })
    notify.toast.success(`已忽略 ${result.rejected} 条建议`)
    emit('changed')
    await load()
  } catch (err) {
    notify.fromError(err, { context: '忽略建议失败' })
  } finally {
    busy.value = false
  }
}

async function rejectAll(): Promise<void> {
  busy.value = true
  try {
    const result = await rejectSuggestions(
      props.jobId ? { groups: groups.value.map((g) => ({ field: g.field, value: g.value })) } : { all: true },
    )
    notify.toast.success(`已忽略 ${result.rejected} 条建议`)
    emit('changed')
    await load()
  } catch (err) {
    notify.fromError(err, { context: '忽略建议失败' })
  } finally {
    busy.value = false
  }
}

watch(
  () => props.show,
  (value) => {
    if (value) void load()
  },
)
</script>

<style scoped lang="less">
.review__empty {
  padding: 24px 0;
  text-align: center;
  color: var(--sm-color-text-muted);
}

.review__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.review__count {
  margin-right: auto;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.review__list {
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 400px;
  overflow: auto;
}

.review__item {
  display: flex;
  gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--sm-color-border);

  &--low {
    opacity: 0.6;
  }
}

.review__body {
  min-width: 0;
  flex: 1;
}

.review__line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.review__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.review__n {
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.review__reason {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.review__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
