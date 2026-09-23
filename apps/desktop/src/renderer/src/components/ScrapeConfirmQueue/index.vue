<template>
  <n-modal :show="show" preset="card" title="确认元数据" style="width: 840px" @update:show="onShow">
    <p v-if="statusText" class="scrape-queue__status">{{ statusText }}</p>
    <div v-if="allowBiliQuery" class="scrape-queue__bv">
      <n-input
        size="small"
        :placeholder="queryPlaceholder || 'BV号、av、视频链接或名称'"
        :value="biliQuery"
        @update:value="biliQuery = $event"
      />
      <n-button size="small" :disabled="busy" @click="researchBili">按此重新搜索</n-button>
    </div>
    <div class="scrape-queue__split">
      <ScrapeCandidateList
        v-if="candidates.length"
        :candidates="candidates"
        :picked-id="pickedId"
        @pick="pickedId = $event"
      />
      <ScrapeApplyFields
        v-if="preview"
        :preview="preview"
        :picked-cover="pickedCover"
        :apply-title="applyTitle"
        :apply-synopsis="applySynopsis"
        :apply-author="applyAuthor"
        :apply-tags="applyTags"
        :apply-catalog="applyCatalog"
        :apply-cover="applyCover"
        :replace-user-cover="replaceUserCover"
        @update:picked-cover="pickedCover = $event"
        @update:apply-title="applyTitle = $event"
        @update:apply-synopsis="applySynopsis = $event"
        @update:apply-author="applyAuthor = $event"
        @update:apply-tags="applyTags = $event"
        @update:apply-catalog="applyCatalog = $event"
        @update:apply-cover="applyCover = $event"
        @update:replace-user-cover="replaceUserCover = $event"
      />
    </div>
    <p v-if="preview && !hasApply" class="scrape-queue__status">至少选择一项写入</p>
    <template #footer>
      <n-button size="small" :disabled="busy" @click="skipAll">全部跳过</n-button>
      <n-button size="small" :disabled="busy" @click="skipOne">跳过</n-button>
      <n-button
        size="small"
        type="primary"
        :loading="busy"
        :disabled="!canConfirm"
        @click="confirmOne"
      >
        确认
      </n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { NButton, NInput, NModal, useMessage } from 'naive-ui'
import {
  createScrapeJob,
  getLatestScrapeJob,
  getScrapeJob,
  listScrapeCandidates,
  previewScrapeCandidate,
  selectScrapeCandidate,
} from '@/infrastructure/http/scrape'
import { invalidateResourceCache } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type { Candidate, ScrapeJob, ScrapePreview } from '@/domain'
import ScrapeCandidateList from './ScrapeCandidateList.vue'
import ScrapeApplyFields from './ScrapeApplyFields.vue'

const props = defineProps<{
  show: boolean
  resourceIds: number[]
  force?: boolean
  preferLatest?: boolean
  allowBiliQuery?: boolean
  queryPlaceholder?: string
  queryEmptyHint?: string
  initialQuery?: string
}>()

const emit = defineEmits<{
  'update:show': [boolean]
  applied: []
}>()

const message = useMessage()
const library = useLibraryStore()
const queue = ref<number[]>([])
const index = ref(0)
const job = ref<ScrapeJob | null>(null)
const candidates = ref<Candidate[]>([])
const pickedId = ref<number | null>(null)
const preview = ref<ScrapePreview | null>(null)
const pickedCover = ref<string | null>(null)
const applyTitle = ref(true)
const applySynopsis = ref(true)
const applyAuthor = ref(false)
const applyTags = ref(true)
const applyCatalog = ref(true)
const applyCover = ref(true)
const replaceUserCover = ref(false)
const busy = ref(false)
const statusText = ref('')
const biliQuery = ref('')
let pollTimer: ReturnType<typeof setTimeout> | undefined
let gen = 0

const hasApply = computed(
  () =>
    applyTitle.value ||
    applySynopsis.value ||
    applyAuthor.value ||
    applyTags.value ||
    applyCatalog.value ||
    applyCover.value
)
const canConfirm = computed(
  () => pickedId.value != null && job.value?.status === 'done' && hasApply.value && !busy.value
)

function onShow(next: boolean): void {
  emit('update:show', next)
}

function clearPoll(): void {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = undefined
  }
}

function skipAll(): void {
  gen += 1
  clearPoll()
  busy.value = false
  emit('update:show', false)
}

async function skipOne(): Promise<void> {
  await advance()
}

async function advance(): Promise<void> {
  clearPoll()
  gen += 1
  index.value += 1
  pickedId.value = null
  preview.value = null
  pickedCover.value = null
  candidates.value = []
  job.value = null
  if (index.value >= queue.value.length) {
    busy.value = false
    emit('update:show', false)
    return
  }
  await loadCurrent()
}

async function loadPreview(candidateId: number): Promise<void> {
  const jobId = job.value?.id
  if (jobId == null) return
  const mine = gen
  try {
    const row = await previewScrapeCandidate(jobId, candidateId)
    if (mine !== gen || job.value?.id !== jobId || pickedId.value !== candidateId) return
    preview.value = row
    pickedCover.value = row.coverUrls[0] ?? null
    applyTitle.value = true
    applySynopsis.value = Boolean(row.synopsis)
    applyAuthor.value = !(row.current?.author || '').trim() && Boolean(row.author)
    applyTags.value = row.tags.length > 0
    applyCatalog.value = true
    applyCover.value = row.coverUrls.length > 0
    replaceUserCover.value = false
  } catch (err) {
    if (mine !== gen) return
    preview.value = null
    message.warning(err instanceof Error ? err.message : '封面预览失败')
  }
}

async function confirmOne(): Promise<void> {
  if (job.value?.id == null || pickedId.value == null) return
  const mine = gen
  busy.value = true
  try {
    await selectScrapeCandidate(job.value.id, {
      candidateId: pickedId.value,
      coverUrl: pickedCover.value,
      applyTitle: applyTitle.value,
      applySynopsis: applySynopsis.value,
      applyAuthor: applyAuthor.value,
      applyTags: applyTags.value,
      applyCatalog: applyCatalog.value,
      applyCover: applyCover.value,
      replaceUserCover: replaceUserCover.value,
    })
    if (mine !== gen) return
    invalidateResourceCache()
    library.bump(null)
    emit('applied')
    await advance()
  } catch (err) {
    if (mine !== gen) return
    message.error(err instanceof Error ? err.message : '回填失败')
    busy.value = false
  }
}

async function loadCurrent(): Promise<void> {
  const mine = gen
  const resourceId = queue.value[index.value]
  if (resourceId == null) return
  statusText.value = `第 ${index.value + 1} / ${queue.value.length} 条`
  busy.value = true
  preview.value = null
  pickedId.value = null
  pickedCover.value = null
  applyCover.value = true
  replaceUserCover.value = false
  try {
    const typed = props.allowBiliQuery ? biliQuery.value.trim() : ''
    if (typed) {
      job.value = await createScrapeJob(resourceId, true, typed)
    } else if (props.preferLatest && props.force !== true) {
      job.value = await getLatestScrapeJob(resourceId)
    } else {
      job.value = await createScrapeJob(resourceId, props.force === true)
    }
    if (mine !== gen) return
    if (job.value.id == null) {
      busy.value = false
      statusText.value = '任务无效'
      return
    }
    await waitUntilSettled(job.value.id, mine)
  } catch (err) {
    if (mine !== gen) return
    statusText.value = err instanceof Error ? err.message : '搜索失败'
    busy.value = false
  }
}

async function waitUntilSettled(jobId: number, mine: number): Promise<void> {
  clearPoll()
  const tick = async (): Promise<void> => {
    if (mine !== gen) return
    try {
      const row = await getScrapeJob(jobId)
      if (mine !== gen) return
      job.value = row
      if (row.status === 'queued' || row.status === 'running') {
        statusText.value = `第 ${index.value + 1} / ${queue.value.length} 条 · 搜索中`
        pollTimer = setTimeout(() => void tick(), 400)
        return
      }
      busy.value = false
      if (row.status === 'failed') {
        statusText.value = row.error || '搜索失败'
        candidates.value = []
        return
      }
      candidates.value = await listScrapeCandidates(jobId)
      if (mine !== gen) return
      const firstId = candidates.value.find((item) => item.id != null)?.id ?? null
      pickedId.value = firstId
      if (candidates.value.length === 0) {
        statusText.value = `第 ${index.value + 1} / ${queue.value.length} 条 · 无候选`
      } else {
        statusText.value = `第 ${index.value + 1} / ${queue.value.length} 条`
      }
    } catch (err) {
      if (mine !== gen) return
      busy.value = false
      statusText.value = err instanceof Error ? err.message : '搜索失败'
    }
  }
  await tick()
}

watch(pickedId, (id) => {
  preview.value = null
  pickedCover.value = null
  if (id == null || job.value?.id == null) return
  void loadPreview(id)
})

async function researchBili(): Promise<void> {
  const resourceId = queue.value[index.value]
  const typed = biliQuery.value.trim()
  if (resourceId == null || !typed) {
    message.warning(props.queryEmptyHint || '请填写 BV 号、链接或视频名称')
    return
  }
  clearPoll()
  gen += 1
  const mine = gen
  busy.value = true
  preview.value = null
  pickedId.value = null
  pickedCover.value = null
  candidates.value = []
  try {
    job.value = await createScrapeJob(resourceId, true, typed)
    if (mine !== gen) return
    if (job.value.id == null) {
      busy.value = false
      statusText.value = '任务无效'
      return
    }
    await waitUntilSettled(job.value.id, mine)
  } catch (err) {
    if (mine !== gen) return
    statusText.value = err instanceof Error ? err.message : '搜索失败'
    busy.value = false
  }
}

watch(
  () => [props.show, props.force, props.preferLatest, props.resourceIds.join(',')] as const,
  () => {
    clearPoll()
    gen += 1
    if (!props.show) {
      queue.value = []
      job.value = null
      candidates.value = []
      preview.value = null
      pickedId.value = null
      pickedCover.value = null
      busy.value = false
      return
    }
    biliQuery.value = props.initialQuery ?? ''
    queue.value = [...props.resourceIds]
    index.value = 0
    void loadCurrent()
  }
)

onUnmounted(() => {
  gen += 1
  clearPoll()
})
</script>

<style scoped lang="less">
.scrape-queue__bv {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: var(--sm-space-2);
}

.scrape-queue__status {
  margin: 0 0 var(--sm-space-2);
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.scrape-queue__split {
  display: flex;
  gap: var(--sm-space-3);
  align-items: stretch;
  height: min(72vh, 560px);
  min-height: 0;
  overflow: hidden;
}
</style>
