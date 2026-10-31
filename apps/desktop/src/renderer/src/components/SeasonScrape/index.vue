<template>
  <n-modal :show="show" preset="card" :title="`刮削第 ${season} 季`" style="width: 560px" @update:show="onShow">
    <p class="season-scrape__hint">
      {{ statusText }}
    </p>
    <p v-if="query" class="muted">搜索词：{{ query }}</p>

    <ul v-if="candidates.length" class="season-scrape__list">
      <li v-for="item in candidates" :key="item.id ?? item.title" class="season-scrape__item">
        <img
          v-if="item.thumbnailUrl"
          class="season-scrape__thumb"
          :src="scrapeImageSrc(item.thumbnailUrl)"
          alt=""
        />
        <div class="season-scrape__body">
          <strong>{{ item.title }}</strong>
          <span class="muted">{{ item.source }}</span>
        </div>
        <n-button size="small" :disabled="busy" @click="applyCandidate(item)">使用</n-button>
      </li>
    </ul>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="season-scrape__actions">
      <n-button :disabled="busy" @click="onShow(false)">关闭</n-button>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NModal, NButton } from 'naive-ui'
import {
  createScrapeJob,
  getScrapeJob,
  listScrapeCandidates,
  scrapeImageSrc,
  selectScrapeCandidate,
} from '@/infrastructure/http'
import type { Candidate } from '@/domain'

const props = defineProps<{
  show: boolean
  resourceId: number
  season: number
  seasonTitle?: string | null
}>()

const emit = defineEmits<{
  'update:show': [boolean]
  applied: []
}>()

const candidates = ref<Candidate[]>([])
const busy = ref(false)
const error = ref('')
const jobId = ref<number | null>(null)

const query = computed(() => props.seasonTitle?.trim() || '')
const statusText = computed(() => {
  if (busy.value) return '正在搜索与整理候选…'
  if (candidates.value.length) return `找到 ${candidates.value.length} 个候选`
  if (error.value) return '刮削失败'
  return '选择一条候选写入本季'
})

function onShow(next: boolean): void {
  if (!next) emit('update:show', false)
}

async function run(): Promise<void> {
  candidates.value = []
  error.value = ''
  jobId.value = null
  if (!props.show || !props.resourceId) return
  busy.value = true
  try {
    const job = await createScrapeJob(props.resourceId, true, query.value || undefined)
    if (job.id == null) {
      error.value = '任务创建失败'
      return
    }
    jobId.value = job.id
    let current = job
    for (let attempt = 0; attempt < 60 && current.status !== 'done' && current.status !== 'failed'; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      current = await getScrapeJob(job.id)
    }
    if (current.status !== 'done') {
      error.value = current.error || '刮削没有完成'
      return
    }
    candidates.value = await listScrapeCandidates(job.id)
  } catch {
    error.value = '刮削失败，请稍后再试'
  } finally {
    busy.value = false
  }
}

async function applyCandidate(item: Candidate): Promise<void> {
  if (jobId.value == null || item.id == null) return
  busy.value = true
  error.value = ''
  try {
    await selectScrapeCandidate(jobId.value, {
      candidateId: item.id,
      season: props.season,
      applyTitle: true,
      applyCatalog: true,
      applySynopsis: false,
      applyAuthor: false,
      applyTags: false,
      applyCover: false,
    })
    emit('applied')
    onShow(false)
  } catch {
    error.value = '写入失败'
  } finally {
    busy.value = false
  }
}

watch(
  () => [props.show, props.resourceId, props.season] as const,
  () => {
    void run()
  },
  { immediate: true },
)
</script>

<style scoped lang="less">
.season-scrape__hint {
  margin: 0 0 6px;
  font-size: 13px;
}

.season-scrape__list {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  max-height: 320px;
  overflow: auto;
}

.season-scrape__item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--sm-color-border);
}

.season-scrape__thumb {
  width: 40px;
  height: 56px;
  object-fit: cover;
  border-radius: 4px;
}

.season-scrape__body {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  font-size: 12px;
}

.season-scrape__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
