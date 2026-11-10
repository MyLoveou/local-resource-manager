<template>
  <div v-if="visible" class="update-banner">
    <div class="update-banner__main">
      <span class="update-banner__badge">更新</span>
      <span class="update-banner__text">
        <template v-if="status.phase === 'available'">
          发现新版本 {{ status.version }}（当前 {{ status.currentVersion }}）
        </template>
        <template v-else-if="status.phase === 'downloading'">
          正在下载 {{ status.version }}… {{ status.percent ?? 0 }}%
        </template>
        <template v-else>
          {{ status.version }} 已下载，重启后完成更新
        </template>
      </span>
      <n-progress
        v-if="status.phase === 'downloading'"
        class="update-banner__progress"
        type="line"
        :percentage="status.percent ?? 0"
        :show-indicator="false"
        :height="4"
      />
      <div class="update-banner__actions">
        <n-button
          v-if="status.phase === 'available'"
          size="tiny"
          quaternary
          @click="showNotes = !showNotes"
        >
          更新公告
        </n-button>
        <n-button
          v-if="status.phase === 'available'"
          size="tiny"
          type="primary"
          @click="update.download()"
        >
          下载更新
        </n-button>
        <n-button
          v-if="status.phase === 'downloaded'"
          size="tiny"
          type="primary"
          @click="update.install()"
        >
          重启安装
        </n-button>
        <n-button
          v-if="status.phase === 'available'"
          size="tiny"
          quaternary
          @click="dismissed = true"
        >
          稍后
        </n-button>
        <n-button
          v-if="status.phase === 'downloaded'"
          size="tiny"
          quaternary
          @click="dismissed = true"
        >
          稍后
        </n-button>
      </div>
    </div>
    <pre v-if="showNotes && status.releaseNotes" class="update-banner__notes">{{ status.releaseNotes }}</pre>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NProgress } from 'naive-ui'
import { useUpdateStore } from '@/application/stores/update'

const update = useUpdateStore()
const status = computed(() => update.status)
const dismissed = ref(false)
const showNotes = ref(false)

const visible = computed(() => {
  if (dismissed.value) return false
  return ['available', 'downloading', 'downloaded'].includes(status.value.phase)
})

watch(
  () => status.value.phase,
  (phase) => {
    if (phase === 'downloaded') dismissed.value = false
  }
)

onMounted(() => {
  void update.init()
})
</script>

<style scoped lang="less">
.update-banner {
  flex-shrink: 0;
  padding: 6px var(--sm-space-3);
  background: color-mix(in srgb, var(--sm-color-primary, #2563eb) 10%, transparent);
  border-bottom: 1px solid var(--sm-color-border);
  color: var(--sm-color-text);
  font-size: 12px;
}

.update-banner__main {
  display: flex;
  align-items: center;
  gap: var(--sm-space-2);
}

.update-banner__badge {
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--sm-color-primary, #2563eb);
  color: #fff;
  font-size: 11px;
}

.update-banner__text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.update-banner__progress {
  width: 160px;
  flex-shrink: 0;
}

.update-banner__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
}

.update-banner__notes {
  max-height: 160px;
  overflow: auto;
  margin: 6px 0 0;
  padding: 8px;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 12px;
  color: var(--sm-color-text-muted);
  background: var(--sm-color-bg-surface);
  border-radius: var(--sm-radius-control);
}
</style>
