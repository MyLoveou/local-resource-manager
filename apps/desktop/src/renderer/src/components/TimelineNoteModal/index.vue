<template>
  <n-modal
    :show="show"
    preset="card"
    :title="title"
    style="width: 460px"
    :mask-closable="!busy"
    @update:show="(value: boolean) => emit('update:show', value)"
  >
    <div class="timeline-note-form">
      <n-input
        v-model:value="form.title"
        placeholder="标题（可选，如 C104 Day1）"
        :maxlength="200"
        :disabled="busy"
      />
      <n-input
        v-model:value="form.body"
        type="textarea"
        :rows="4"
        placeholder="备注内容"
        :maxlength="5000"
        :disabled="busy"
      />
      <n-input
        v-model:value="form.location"
        placeholder="地点（可选，如东京国际展示场）"
        :maxlength="200"
        :disabled="busy"
      />
      <p class="timeline-note-form__hint">
        地点只保存名称，不修改照片 EXIF；地图使用照片自带 GPS。
      </p>
    </div>
    <template #footer>
      <div class="timeline-note-form__actions">
        <n-button v-if="note" size="small" type="error" ghost :disabled="busy" @click="remove">
          删除备注
        </n-button>
        <span class="timeline-note-form__spacer" />
        <n-button size="small" :disabled="busy" @click="close">取消</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="save">保存</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { NButton, NInput, NModal } from 'naive-ui'
import { notify } from '@/application/notify'
import {
  deleteDateNote,
  deleteSavedViewNote,
  upsertDateNote,
  upsertSavedViewNote,
  type TimelineNote,
} from '@/infrastructure/http'

const props = defineProps<{
  show: boolean
  date?: string | null
  savedViewId?: number | null
  note?: TimelineNote | null
}>()
const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: [note: TimelineNote]
  deleted: []
}>()

const form = reactive({ title: '', body: '', location: '' })
const busy = ref(false)
const title = computed(() => (props.date ? `日期备注 · ${props.date}` : '时间线备注'))

function reset(): void {
  form.title = props.note?.title ?? ''
  form.body = props.note?.body ?? ''
  form.location = props.note?.locationName ?? ''
}

watch(
  () => [props.show, props.note] as const,
  ([show]) => {
    if (show) reset()
  },
  { immediate: true },
)

function close(): void {
  emit('update:show', false)
}

async function save(): Promise<void> {
  if (busy.value) return
  busy.value = true
  try {
    const body = {
      title: form.title,
      body: form.body,
      locationName: form.location,
    }
    const saved = props.date
      ? await upsertDateNote(props.date, body)
      : await upsertSavedViewNote(props.savedViewId as number, body)
    emit('saved', saved)
    emit('update:show', false)
    notify.toast.success('备注已保存')
  } catch (error) {
    notify.fromError(error, { context: '保存备注' })
  } finally {
    busy.value = false
  }
}

async function remove(): Promise<void> {
  if (!props.note || busy.value) return
  busy.value = true
  try {
    if (props.date) await deleteDateNote(props.date)
    else if (props.savedViewId != null) await deleteSavedViewNote(props.savedViewId)
    emit('deleted')
    emit('update:show', false)
    notify.toast.success('备注已删除')
  } catch (error) {
    notify.fromError(error, { context: '删除备注' })
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="less">
.timeline-note-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline-note-form__hint {
  margin: 0;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.timeline-note-form__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-note-form__spacer {
  flex: 1;
}
</style>
