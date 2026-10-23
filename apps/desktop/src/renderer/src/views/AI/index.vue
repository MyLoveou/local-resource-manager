<template>
  <div class="ai-center">
    <header class="ai-center__head">
      <div>
        <h2>AI 中心</h2>
        <p>本地中文搜图、模型与索引任务；图片不会上传。</p>
      </div>
      <n-tag :type="statusTagType" size="small" :bordered="false">{{ statusLabel }}</n-tag>
    </header>

    <n-button-group class="ai-center__tabs" size="small">
      <n-button
        v-for="tab in tabs"
        :key="tab.value"
        :type="activeTab === tab.value ? 'primary' : 'default'"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </n-button>
    </n-button-group>

    <p v-if="ai.error" class="ai-center__error">{{ ai.error }}</p>

    <template v-if="activeTab === 'search'">
      <section v-if="!ai.modelInstalled" class="ai-setup">
        <h3>安装中文 CLIP 模型</h3>
        <p>首次使用需要下载约 195 MB 的本地模型。安装后可离线用文字搜索图片。</p>
        <div class="ai-setup__actions">
          <n-button type="primary" :loading="ai.jobActive" @click="install">
            安装模型
          </n-button>
          <span v-if="ai.job?.kind === 'install' && ai.jobActive" class="ai-muted">
            {{ jobProgressText }}
          </span>
        </div>
        <n-progress
          v-if="ai.job?.kind === 'install' && ai.jobActive"
          type="line"
          :percentage="jobPercent"
          :height="6"
        />
      </section>

      <template v-else>
        <section v-if="!ai.canSearch" class="ai-setup">
          <h3>建立图片索引</h3>
          <p>
            当前图库有 {{ ai.total }} 张图片，已索引 {{ ai.indexed }} 张。
            首次索引只在本机计算向量。
          </p>
          <div class="ai-setup__actions">
            <n-button type="primary" :loading="ai.jobActive" @click="index">
              {{ ai.indexed > 0 ? '重新建立索引' : '建立索引' }}
            </n-button>
            <span v-if="ai.job?.kind === 'index' && ai.jobActive" class="ai-muted">
              {{ jobProgressText }}
            </span>
          </div>
          <n-progress
            v-if="ai.job?.kind === 'index' && ai.jobActive"
            type="line"
            :percentage="jobPercent"
            :height="6"
          />
        </section>

        <template v-else>
          <div class="ai-searchbar">
            <n-input
              v-model:value="query"
              size="small"
              clearable
              placeholder="用中文描述图片，例如：海边、两个人、红帽子"
              :disabled="ai.jobActive"
              @keydown.enter.prevent="runSearch"
            />
            <n-button
              type="primary"
              size="small"
              :loading="ai.searching"
              :disabled="ai.jobActive"
              @click="runSearch"
            >
              搜索
            </n-button>
          </div>
          <p v-if="ai.jobActive" class="ai-muted">索引重建中，完成后即可搜索。</p>
          <p class="ai-muted">
            已索引 {{ ai.results?.indexed ?? ai.indexed }} 张
            <template v-if="ai.results">
              · 匹配 {{ ai.results.matched }} 张 · 显示 {{ ai.results.returned }} 张
            </template>
          </p>
          <div v-if="ai.results?.filters.length" class="ai-filters">
            <n-tag v-for="filter in ai.results.filters" :key="filter" size="small" :bordered="false">
              {{ filter }}
            </n-tag>
          </div>

          <div v-if="ai.searching" class="ai-empty">
            <n-spin size="small" /> 正在计算相似度
          </div>
          <div v-else-if="ai.results?.items.length" class="ai-results">
            <button
              v-for="(item, index) in ai.results.items"
              :key="item.id"
              type="button"
              class="ai-result"
              @click="openResult(item)"
            >
              <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
              <span class="ai-result__score">
                {{ scoreLabel(ai.results.scores[index] ?? 0) }}
              </span>
              <span class="ai-result__title">{{ item.title }}</span>
            </button>
          </div>
          <div v-else-if="ai.results && ai.results.matched === 0" class="ai-empty">
            没有符合当前特征的图片。
          </div>
          <div v-else-if="ai.results" class="ai-empty">
            没有找到相近图片，换一种说法试试。
          </div>
          <div v-else class="ai-empty">
            输入描述后开始搜索。
          </div>
        </template>
      </template>
    </template>

    <template v-else-if="activeTab === 'similar'">
      <section v-if="!similarSource" class="ai-setup">
        <h3>以图搜图</h3>
        <p>从图片查看器或 Inspector 的「找相似」进入，选择一张查询图片。</p>
      </section>

      <template v-else>
        <section class="ai-similar-source">
          <img :src="resolveCardImageUrl(similarSource)" :alt="similarSource.title" />
          <div>
            <strong>{{ similarSource.title }}</strong>
            <p class="ai-muted">查询图不会出现在结果中。</p>
          </div>
        </section>

        <div class="ai-similar-modes">
          <n-button-group size="small">
            <n-button
              v-for="mode in similarModes"
              :key="mode.value"
              :type="similarMode === mode.value ? 'primary' : 'default'"
              @click="changeSimilarMode(mode.value)"
            >
              {{ mode.label }}
            </n-button>
          </n-button-group>
          <span class="ai-muted">
            已索引 {{ similar?.indexed ?? 0 }} 张
            · 返回 {{ similar?.returned ?? 0 }} 张
          </span>
        </div>

        <p v-if="similarError" class="ai-center__error">{{ similarError }}</p>
        <div v-if="similarLoading" class="ai-empty">
          <n-spin size="small" /> 正在计算相似度
        </div>

        <template v-else-if="similar">
          <section v-if="similar.duplicates.length" class="ai-panel">
            <div class="ai-panel__row">
              <strong>近似重复</strong>
              <n-tag size="small" :bordered="false">{{ similar.duplicates.length }} 张</n-tag>
            </div>
            <div class="ai-results">
              <button
                v-for="(item, index) in similar.duplicates"
                :key="`dup-${item.id}`"
                type="button"
                class="ai-result"
                @click="openDuplicateResult(item)"
              >
                <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
                <span class="ai-result__score">重复 {{ ((similar.duplicateScores[index] ?? 0) * 100).toFixed(0) }}%</span>
                <span class="ai-result__title">{{ item.title }}</span>
              </button>
            </div>
          </section>

          <section v-if="similar.items.length" class="ai-panel">
            <div class="ai-panel__row">
              <strong>相似图片</strong>
              <n-tag size="small" :bordered="false">{{ similar.items.length }} 张</n-tag>
            </div>
            <div class="ai-results">
              <button
                v-for="(item, index) in similar.items"
                :key="`similar-${item.id}`"
                type="button"
                class="ai-result"
                @click="openSimilarResult(item)"
              >
                <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
                <span class="ai-result__score">
                  {{ scoreLabel(similar.scores[index] ?? 0) }}
                </span>
                <span class="ai-result__title">{{ item.title }}</span>
              </button>
            </div>
          </section>

          <div v-if="similar.duplicates.length === 0 && similar.items.length === 0" class="ai-empty">
            没有找到相近图片。
          </div>
        </template>
      </template>
    </template>

    <section v-else-if="activeTab === 'models'" class="ai-panel">
      <div class="ai-panel__row">
        <strong>中文 CLIP</strong>
        <n-tag size="small" :bordered="false" :type="ai.modelInstalled ? 'success' : 'warning'">
          {{ ai.modelInstalled ? '已安装' : '未安装' }}
        </n-tag>
      </div>
      <p class="ai-muted">
        Chinese-CLIP ViT-B/16 + YOLOv8n 人物检测 · 512 维 · 约 195 MB · 本地 CPU 推理
      </p>
      <p class="ai-muted">
        已索引 {{ ai.status?.indexed ?? 0 }} 张 · 人数特征
        {{ ai.status?.personCountIndexed ?? 0 }} 张
      </p>
      <p class="ai-muted">
        模型会下载到本机数据目录；不会把图片或描述发到外部服务。
      </p>
      <div class="ai-panel__actions">
        <n-button
          v-if="!ai.modelInstalled"
          type="primary"
          :loading="ai.jobActive"
          @click="install"
        >
          安装模型
        </n-button>
        <n-button
          v-else
          :loading="ai.jobActive"
          @click="index"
        >
          {{ ai.indexed > 0 ? '重新建立索引' : '建立索引' }}
        </n-button>
      </div>
      <n-progress
        v-if="ai.jobActive"
        class="ai-panel__progress"
        type="line"
        :percentage="jobPercent"
        :height="6"
      />
      <p v-if="ai.jobActive" class="ai-muted">{{ jobProgressText }}</p>
    </section>

    <section v-else-if="activeTab === 'jobs'" class="ai-panel">
      <div class="ai-panel__row">
        <strong>{{ ai.job ? jobTitle(ai.job.kind) : '暂无任务' }}</strong>
        <n-tag v-if="ai.job" size="small" :bordered="false">{{ jobStatusLabel }}</n-tag>
      </div>
      <template v-if="ai.job">
        <n-progress
          v-if="ai.job.status === 'queued' || ai.job.status === 'running'"
          type="line"
          :percentage="jobPercent"
          :height="6"
        />
        <p class="ai-muted">{{ ai.job.message || jobProgressText }}</p>
        <p v-if="ai.job.status === 'error'" class="ai-center__error">{{ ai.job.message }}</p>
      </template>
      <p v-else class="ai-muted">安装模型或建立索引后，任务进度会显示在这里。</p>
    </section>

    <section v-else class="ai-panel">
      <div class="ai-panel__row">
        <strong>AI 建议</strong>
        <n-tag size="small" :bordered="false">待接入</n-tag>
      </div>
      <p class="ai-muted">
        后续会在这里审核 AI 生成的标签、角色、扮演者和合集建议。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NButtonGroup, NInput, NProgress, NSpin, NTag } from 'naive-ui'
import { useAIStore } from '@/application/stores/ai'
import { openResource } from '@/infrastructure/consume/consumeResource'
import { getAISimilar, getResource, resolveCardImageUrl } from '@/infrastructure/http'
import type { AISimilarResult } from '@/infrastructure/http'
import type { Resource } from '@/domain'

const tabs = [
  { value: 'search', label: '搜索' },
  { value: 'similar', label: '找相似' },
  { value: 'models', label: '模型' },
  { value: 'jobs', label: '任务' },
  { value: 'suggestions', label: '建议' },
] as const

const similarModes = [
  { value: 'auto', label: '综合' },
  { value: 'semantic', label: '语义' },
  { value: 'duplicate', label: '近似重复' },
] as const

type TabValue = (typeof tabs)[number]['value']

const ai = useAIStore()
const route = useRoute()
const router = useRouter()
const activeTab = ref<TabValue>(readTab(route.query.tab))
const query = ref(String(route.query.q ?? ''))
const similar = ref<AISimilarResult | null>(null)
const similarSource = ref<Resource | null>(null)
const similarLoading = ref(false)
const similarMode = ref<'auto' | 'semantic' | 'duplicate'>('auto')
const similarError = ref('')

function readTab(value: unknown): TabValue {
  return tabs.some((tab) => tab.value === value) ? (value as TabValue) : 'search'
}

const statusLabel = computed(() => {
  if (ai.loading && !ai.status) return '检测中'
  if (ai.status?.dependencyReady === false) return '依赖缺失'
  if (!ai.modelInstalled) return 'AI 未启用'
  if (ai.indexed > 0) return 'AI 就绪'
  return '等待索引'
})

const statusTagType = computed(() => {
  if (!ai.modelInstalled || ai.status?.dependencyReady === false) return 'warning'
  if (ai.indexed > 0) return 'success'
  return 'info'
})

const jobPercent = computed(() => ai.job?.percent ?? 0)
const jobProgressText = computed(() => {
  const job = ai.job
  if (!job) return ''
  if (job.total > 0) return `${job.done}/${job.total}`
  return job.message || ''
})
const jobStatusLabel = computed(() => {
  switch (ai.job?.status) {
    case 'queued':
      return '排队中'
    case 'running':
      return '进行中'
    case 'done':
      return '已完成'
    case 'error':
      return '失败'
    default:
      return ai.job?.status ?? ''
  }
})

function jobTitle(kind: string): string {
  return kind === 'install' ? '下载模型' : kind === 'index' ? '建立索引' : 'AI 任务'
}

function scoreLabel(score: number): string {
  return `相似度 ${score.toFixed(2)}`
}

async function runSearch(): Promise<void> {
  if (!ai.canSearch) return
  await ai.search(query.value)
}

async function loadSimilar(resourceId: number): Promise<void> {
  similarLoading.value = true
  similarError.value = ''
  try {
    similarSource.value = await getResource(resourceId)
    similar.value = await getAISimilar(resourceId, similarMode.value)
  } catch (error) {
    similarError.value = error instanceof Error ? error.message : '????????'
    similar.value = null
  } finally {
    similarLoading.value = false
  }
}

async function changeSimilarMode(mode: 'auto' | 'semantic' | 'duplicate'): Promise<void> {
  similarMode.value = mode
  const id = Number(route.query.resourceId)
  if (Number.isFinite(id) && id > 0) await loadSimilar(id)
}

function openSimilarResult(item: Resource): void {
  const ids = (similar.value?.items ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

function openDuplicateResult(item: Resource): void {
  const ids = (similar.value?.duplicates ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

function openSimilarCenter(resourceId: number): void {
  void router.push({ path: '/ai', query: { tab: 'similar', resourceId: String(resourceId) } })
}

async function install(): Promise<void> {
  if (ai.jobActive) return
  await ai.installModel()
}

async function index(): Promise<void> {
  if (ai.jobActive) return
  await ai.buildIndex()
}

function openResult(item: Resource): void {
  const ids = (ai.results?.items ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = readTab(value)
  },
)

watch(
  () => route.query.resourceId,
  async (value) => {
    const id = Number(value)
    if (value && Number.isFinite(id) && id > 0) {
      activeTab.value = 'similar'
      await loadSimilar(id)
    }
  },
)

onMounted(async () => {
  await ai.refresh()
  const id = Number(route.query.resourceId)
  if (route.query.tab === 'similar' && Number.isFinite(id) && id > 0) {
    await loadSimilar(id)
  } else if (query.value) {
    await runSearch()
  }
})
</script>

<style scoped lang="less">
.ai-center {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.ai-center__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: 20px;
  }

  p {
    margin: 6px 0 0;
    color: var(--sm-color-text-muted);
    font-size: 12px;
  }
}

.ai-center__tabs {
  margin-top: 18px;
}

.ai-center__error {
  margin: 14px 0 0;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--sm-color-danger, #d03050) 35%, transparent);
  border-radius: 8px;
  color: var(--sm-color-danger, #d03050);
  font-size: 12px;
}

.ai-setup,
.ai-panel {
  margin-top: 14px;
  padding: 18px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);
}

.ai-setup {
  h3 {
    margin: 0;
    font-size: 16px;
  }

  p {
    max-width: 620px;
    margin: 8px 0 14px;
    color: var(--sm-color-text-muted);
    font-size: 12px;
    line-height: 1.7;
  }
}

.ai-setup__actions,
.ai-panel__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ai-setup :deep(.n-progress),
.ai-panel__progress {
  margin-top: 12px;
}

.ai-panel__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-panel__actions {
  margin-top: 16px;
}

.ai-similar-source {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);

  img {
    width: 160px;
    height: 120px;
    object-fit: cover;
    border-radius: 8px;
    background: var(--sm-color-bg-muted);
  }
}

.ai-similar-modes {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.ai-searchbar {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  padding: 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 10px;
  background: var(--sm-color-bg-surface);
}

.ai-muted {
  margin: 8px 0 0;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.ai-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.ai-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.ai-result {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sm-color-text);
  text-align: left;
  cursor: pointer;

  img {
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    border-radius: 8px;
    background: var(--sm-color-bg-muted);
  }

  &:hover img {
    outline: 2px solid var(--sm-color-accent);
    outline-offset: 2px;
  }
}

.ai-result__score {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgb(0 0 0 / 62%);
  color: #fff;
  font-size: 10px;
}

.ai-result__title {
  overflow: hidden;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 220px;
  margin-top: 12px;
  border: 1px dashed var(--sm-color-border);
  border-radius: 10px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}
</style>
