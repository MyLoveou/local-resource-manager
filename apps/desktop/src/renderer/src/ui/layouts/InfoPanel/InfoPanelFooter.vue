<template>
  <div class="info-panel-footer">
    <div class="info-panel-actions">
      <n-button size="small" :loading="saving" :disabled="!dirty" @click="emit('save')">
        保存
      </n-button>
      <n-button
        v-if="resourceType === 'image'"
        size="small"
        :loading="thumbnailBusy"
        @click="emit('rebuild-thumbnail')"
      >
        重建缩略图
      </n-button>
      <n-input
        v-if="needsScrapeQuery"
        size="small"
        :placeholder="scrapeQueryPlaceholder"
        :value="scrapeQuery"
        style="width: 220px"
        @update:value="emit('update:scrape-query', $event)"
      />
      <n-button
        v-if="isShellOpen"
        size="small"
        :disabled="!canShellOpen || shellBusy"
        @click="emit('open-default')"
      >
        {{ shellActionLabel }}
      </n-button>
      <n-button size="small" @click="emit('edit')">编辑</n-button>
      <n-dropdown
        v-if="moreOptions.length > 0"
        trigger="click"
        :options="moreOptions"
        @select="emit('more', $event)"
      >
        <n-button size="small">更多</n-button>
      </n-dropdown>
      <n-popconfirm
        v-if="resourceStatus !== 'trashed'"
        positive-text="确认"
        negative-text="取消"
        @positive-click="emit('delete')"
      >
        <template #trigger>
          <n-button size="small" type="error" :disabled="deleting" ghost>移到回收站</n-button>
        </template>
        资源会进入回收站，之后仍可恢复。
      </n-popconfirm>
      <n-popconfirm
        v-else
        positive-text="确认"
        negative-text="取消"
        @positive-click="emit('restore')"
      >
        <template #trigger>
          <n-button size="small" :disabled="deleting">恢复</n-button>
        </template>
        从回收站恢复这个资源。
      </n-popconfirm>
      <n-popconfirm
        v-if="resourceStatus === 'trashed'"
        positive-text="彻底删除"
        negative-text="取消"
        @positive-click="emit('purge')"
      >
        <template #trigger>
          <n-button size="small" type="error" :disabled="deleting" ghost>彻底删除</n-button>
        </template>
        彻底删除会移除库内文件，且不可撤销。
      </n-popconfirm>
    </div>
    <p v-if="errorMessage" class="info-panel-error">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { NButton, NDropdown, NInput, NPopconfirm } from 'naive-ui'
import type { DropdownOption } from 'naive-ui'
import type { ResourceType } from '@/domain'

defineProps<{
  saving: boolean
  dirty: boolean
  resourceType: ResourceType
  thumbnailBusy: boolean
  needsScrapeQuery: boolean
  scrapeQueryPlaceholder: string
  scrapeQuery: string
  isShellOpen: boolean
  canShellOpen: boolean
  shellBusy: boolean
  shellActionLabel: string
  moreOptions: DropdownOption[]
  deleting: boolean
  resourceStatus: string
  errorMessage: string
}>()

const emit = defineEmits<{
  save: []
  'rebuild-thumbnail': []
  'update:scrape-query': [value: string]
  'open-default': []
  edit: []
  more: [key: string | number]
  delete: []
  restore: []
  purge: []
}>()
</script>

<style scoped lang="less">
.info-panel-footer {
  padding: 12px 0 4px;
  border-top: 1px solid var(--sm-color-border);
}

.info-panel-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.info-panel-error {
  margin: 8px 0 0;
  color: var(--sm-color-danger, #d03050);
  font-size: 12px;
}
</style>
