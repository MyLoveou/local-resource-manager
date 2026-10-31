<template>
  <n-modal
    :show="visible"
    preset="card"
    title="导入"
    style="width: 520px"
    :mask-closable="!busy"
    :closable="!busy"
    @update:show="onShow"
  >
    <div v-if="step === 'type'" class="wizard-step">
      <p class="hint">选择要导入的资源类型</p>
      <n-radio-group v-model:value="resourceType">
        <n-space>
          <n-radio v-for="item in ENABLED_IMPORT_TYPES" :key="item.value" :value="item.value">
            {{ item.label }}
          </n-radio>
        </n-space>
      </n-radio-group>
      <div v-if="preview" class="wizard-preview">
        <p class="hint">{{ preview.message }}</p>
        <p class="muted">点「选择并导入」并选同一个目录，将直接沿用这份结构，不会重新识别。</p>
        <div v-if="preview.seasons.length" class="wizard-preview__body">
          <div v-for="season in preview.seasons" :key="season.season" class="wizard-preview__season">
            <strong>第 {{ season.season }} 季 · {{ season.episodes.length }} 集</strong>
            <ul>
              <li v-for="ep in season.episodes" :key="ep.episode">
                {{ String(ep.episode).padStart(2, '0') }}
                <span v-if="ep.title"> · {{ ep.title }}</span>
              </li>
            </ul>
          </div>
        </div>
        <p v-if="preview.extras.length" class="muted">
          特典 {{ preview.extras.length }} 个：{{ preview.extras.slice(0, 5).map((item: PreviewExtra) => item.title).join('、') }}
        </p>
        <ul v-if="preview.details.length" class="details">
          <li v-for="(line, index) in preview.details" :key="index">{{ line }}</li>
        </ul>
      </div>
      <div class="actions">
        <n-button type="primary" @click="goSource">下一步</n-button>
      </div>
    </div>

    <div v-else-if="step === 'source'" class="wizard-step">
      <p class="hint">选择来源</p>
      <n-radio-group v-model:value="sourceKind">
        <n-space>
          <n-radio v-if="allowsFileSource(resourceType)" :value="SourceKind.FILE">文件</n-radio>
          <n-radio :value="SourceKind.DIRECTORY">文件夹</n-radio>
        </n-space>
      </n-radio-group>
      <template v-if="allowsMultipleStorage">
        <p class="hint">入库方式</p>
        <n-radio-group v-model:value="storageKind">
          <n-space vertical>
            <n-radio value="indexed">扫描登记（不复制文件，适合已安装游戏）</n-radio>
            <n-radio value="owned">复制进库（便携小游戏）</n-radio>
          </n-space>
        </n-radio-group>
      </template>
      <div v-if="isTimelineMedia" class="timeline-toggle">
        <n-checkbox
          :checked="timelineVisible"
          :disabled="busy"
          @update:checked="(checked: boolean) => (timelineVisible = checked)"
        >
          计入时间线（默认按拍摄时间）
        </n-checkbox>
      </div>
      <div v-if="isMapMedia" class="timeline-toggle">
        <n-checkbox
          :checked="mapVisible"
          :disabled="busy"
          @update:checked="(checked: boolean) => (mapVisible = checked)"
        >
          加入地图（需要 GPS）
        </n-checkbox>
      </div>
      <div class="timeline-toggle">
        <n-checkbox :checked="aiTitle" :disabled="busy" @update:checked="onAiTitleChange">
          用 AI 清洗标题（模型不可用时自动跳过）
        </n-checkbox>
      </div>
      <p class="hint">整理信息（可选，应用整批）</p>
      <n-select
        v-model:value="categoryIds"
        multiple
        filterable
        clearable
        placeholder="导入后加入分类"
        :options="categoryOptions"
        :disabled="busy"
      />
      <n-select
        v-model:value="tagIds"
        multiple
        filterable
        clearable
        placeholder="导入后添加标签"
        :options="tagOptions"
        :disabled="busy"
      />
      <div class="actions">
        <n-button :disabled="busy" @click="step = 'type'">上一步</n-button>
<n-button :disabled="busy || sourceKind !== 'directory'" @click="previewStructure">
          预览结构
        </n-button>
        <n-button type="primary" :disabled="busy" @click="pickAndImport">选择并导入</n-button>
      </div>
    </div>

    <div v-else class="wizard-step">
      <p class="hint">{{ phaseLabel }}</p>
      <n-progress type="line" :percentage="percent" :processing="busy" />
      <p v-if="speedLabel" class="muted">{{ speedLabel }}</p>
      <p v-if="job" class="muted">
        新增 {{ job.imported }} · 跳过重复 {{ job.skippedDuplicate }} · 错误 {{ job.skippedError }}
      </p>
      <p
        v-if="job?.message"
        :class="job.code ? 'error' : 'muted'"
      >{{ job.message }}</p>
      <ul
        v-if="job?.details?.length"
        class="details"
        tabindex="0"
        aria-label="导入说明明细"
      >
        <li v-for="(line, index) in job.details" :key="index">{{ line }}</li>
      </ul>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <div class="actions">
        <n-button
          v-if="job?.status === 'done'"
          :disabled="busy"
          @click="reviewOpen = true"
        >
          查看建议
        </n-button>
        <n-button :disabled="busy" @click="close">完成</n-button>
      </div>
    </div>
    <SuggestionReview v-model:show="reviewOpen" :job-id="job?.jobId ?? null" />
  </n-modal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NModal, NButton, NCheckbox, NRadio, NRadioGroup, NSelect, NSpace, NProgress } from 'naive-ui'
import { notify } from '@/application/notify'
import SuggestionReview from '@/components/SuggestionReview/index.vue'
import { getImportSettings, saveImportSettings } from '@/infrastructure/http/suggestions'
import { ENABLED_IMPORT_TYPES, useLibraryImport } from '@/hooks/useLibraryImport'
import type { PreviewExtra } from '@/infrastructure/http'
import { SourceKind } from '@/domain'

const {
  visible,
  step,
  resourceType,
  sourceKind,
  storageKind,
  timelineVisible,
  mapVisible,
  categoryIds,
  tagIds,
  categoryOptions,
  tagOptions,
  job,
  busy,
  errorMessage,
  allowsFileSource,
  allowsMultipleStorage,
  open,
  close,
  goSource,
  pickAndImport,
  preview,
  previewStructure,
} = useLibraryImport()

const isTimelineMedia = computed(
  () => resourceType.value === 'image' || resourceType.value === 'video'
)
const reviewOpen = ref(false)
const aiTitle = ref(false)

async function onAiTitleChange(checked: boolean): Promise<void> {
  aiTitle.value = checked
  try {
    await saveImportSettings(checked)
  } catch {
    aiTitle.value = !checked
    notify.toast.error('保存 AI 清洗开关失败')
  }
}

onMounted(async () => {
  try {
    aiTitle.value = (await getImportSettings()).aiTitle
  } catch {
    aiTitle.value = false
  }
})
const isMapMedia = computed(
  () => resourceType.value === 'image' || resourceType.value === 'video'
)

const percent = computed(() => {
  if (!job.value) return busy.value ? 10 : 0
  // 后端按阶段折算（校验 30% / 复制 60% / 封面 10%），复制阶段按字节推进
  if (typeof job.value.percent === 'number' && job.value.percent > 0) {
    return Math.min(100, Math.round(job.value.percent))
  }
  if (job.value.total <= 0) return busy.value ? 10 : 0
  return Math.min(100, Math.round((job.value.done / job.value.total) * 100))
})

/** 复制阶段的速率与剩余时间；没有就返回空串 */
const speedLabel = computed(() => {
  const current = job.value
  if (!current || current.phase !== 'copy') return ''
  const parts: string[] = []
  if (current.speedMbps && current.speedMbps > 0) {
    parts.push(`${current.speedMbps.toFixed(0)} MB/s`)
  }
  if (current.etaSeconds && current.etaSeconds > 0) {
    parts.push(`剩余约 ${formatEta(current.etaSeconds)}`)
  }
  return parts.join(' · ')
})

function formatEta(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  if (minutes <= 0) return `${rest} 秒`
  if (minutes < 60) return `${minutes} 分 ${rest} 秒`
  return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分`
}

const phaseLabel = computed(() => {
  if (errorMessage.value) return '导入结束'
  if (!job.value) return busy.value ? '正在准备…' : '等待选择'
  if (job.value.status === 'done' && job.value.skippedError) return '导入结束'
  if (job.value.status === 'done') return '导入完成'
  if (job.value.phase === 'copy') return '正在复制…'
  if (job.value.phase === 'probe') return '正在计算元数据…'
  if (job.value.phase === 'hash') return '正在校验文件…'
  if (job.value.phase === 'cover') return '正在生成封面…'
  if (job.value.phase === 'thumb') return '正在生成缩略图…'
  if (job.value.phase === 'index') return '正在加入抓取队列…'
  return '正在导入…'
})

function onShow(show: boolean): void {
  if (!show) close()
}

defineExpose({ open })
</script>

.wizard-preview { margin: 12px 0; padding: 10px 12px; border: 1px solid var(--sm-color-border); border-radius: 8px; max-height: 260px; overflow: auto; }
.wizard-preview__season { margin-bottom: 8px; font-size: 12px; }
.wizard-preview__season ul { margin: 4px 0 0; padding-left: 18px; columns: 3; }

<style scoped lang="less">
.wizard-step {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hint {
  font-size: 14px;
}

.muted {
  color: #6b7280;
  font-size: 12px;
}

.error {
  color: #d03050;
  font-size: 13px;
}

.details {
  margin: 0;
  padding-left: 1.2em;
  max-height: 180px;
  overflow: auto;
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
  overflow-wrap: anywhere;
  word-break: break-word;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
