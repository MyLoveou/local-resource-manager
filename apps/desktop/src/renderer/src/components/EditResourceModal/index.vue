<template>
  <n-modal
    :show="show"
    preset="card"
    title="编辑资源"
    :style="{ width: '480px' }"
    :mask-closable="false"
    @update:show="onShow"
  >
    <div class="edit-resource">
      <img v-if="coverUrl" class="edit-resource__cover" :src="coverUrl" alt="封面" />
      <n-button v-if="allowCover" size="small" @click="emit('pickCover')">更换封面</n-button>
      <p v-if="allowCover && draft.pendingCoverPath" class="edit-resource__hint">已选择新封面，保存后生效</p>
      <label class="edit-resource__label">标题</label>
      <n-input :value="draft.title" @update:value="draft.title = $event" />
      <label class="edit-resource__label">作品简介</label>
      <n-input
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 6 }"
        :value="draft.synopsis"
        @update:value="draft.synopsis = $event"
      />
      <label class="edit-resource__label">我的评价</label>
      <n-input
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 6 }"
        :value="draft.description"
        @update:value="draft.description = $event"
      />
      <label class="edit-resource__label">评分</label>
      <n-rate allow-half :count="5" :value="draft.ratingStars" @update:value="draft.ratingStars = $event" />
      <label class="edit-resource__label">分类</label>
      <n-select
        filterable
        tag
        clearable
        :options="categoryOptions"
        :value="draft.categoryName"
        @update:value="draft.categoryName = $event"
      />
      <label class="edit-resource__label">标签（Enter 切词，保存后才写入）</label>
      <div class="edit-resource__tags">
        <n-tag v-for="name in draft.tagNames" :key="name" closable @close="removeTag(name)">
          {{ name }}
        </n-tag>
        <n-input
          :value="draft.tagInput"
          placeholder="输入后回车"
          size="small"
          style="width: 140px"
          @update:value="draft.tagInput = $event"
          @keydown.enter.prevent="commitTagInput"
        />
      </div>
    </div>
    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('cancel')">取消</n-button>
        <n-button type="primary" :loading="saving" @click="emit('save')">保存</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { NButton, NInput, NModal, NRate, NSelect, NSpace, NTag } from 'naive-ui'
import type { MetadataDraft } from '@/domain'

const props = defineProps<{
  show: boolean
  draft: MetadataDraft
  categoryOptions: { label: string; value: string }[]
  coverUrl: string
  saving: boolean
  allowCover: boolean
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  save: []
  cancel: []
  pickCover: []
}>()

function onShow(value: boolean): void {
  if (!value) {
    emit('cancel')
    return
  }
  emit('update:show', true)
}

function commitTagInput(): void {
  const text = props.draft.tagInput.trim()
  if (!text) return
  if (!props.draft.tagNames.includes(text)) {
    props.draft.tagNames.push(text)
  }
  props.draft.tagInput = ''
}

function removeTag(name: string): void {
  props.draft.tagNames = props.draft.tagNames.filter((item) => item !== name)
}
</script>

<style scoped lang="less">
.edit-resource {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.edit-resource__cover {
  display: block;
  width: 100%;
  max-width: 100%;
  max-height: 180px;
  object-fit: contain;
}

.edit-resource__hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.edit-resource__label {
  font-size: 12px;
  color: #6b7280;
}

.edit-resource__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.edit-resource__tags :deep(.n-tag) {
  max-width: 100%;
  height: auto;
  white-space: normal;
  overflow-wrap: anywhere;
}
</style>
