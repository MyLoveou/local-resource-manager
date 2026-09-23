<template>
  <n-drawer :show="show" width="420" placement="right" @update:show="onShow">
    <n-drawer-content title="下载" closable>
      <div class="dl-drawer">
        <div class="dl-drawer__form">
          <n-input
            v-model:value="url"
            size="small"
            placeholder="粘贴 HTTP(S) 视频直链或磁力链接"
            @keydown.enter.prevent="start"
          />
          <n-button size="small" type="primary" :loading="busy" @click="start">开始</n-button>
        </div>
        <p v-if="!tasks.length" class="dl-drawer__empty">粘贴 HTTP(S) 视频直链或磁力链接</p>
        <ul v-else class="dl-drawer__list">
          <li v-for="task in tasks" :key="task.id" class="dl-drawer__item">
            <div class="dl-drawer__name">{{ displayName(task) }}</div>
            <div class="dl-drawer__meta">
              {{ statusLabel(task) }}
              <span v-if="task.speed"> · {{ formatSpeed(task.speed) }}</span>
            </div>
            <n-progress
              v-if="task.status === 'running' || task.status === 'paused'"
              type="line"
              :percentage="percent(task)"
              :show-indicator="percent(task) > 0"
            />
            <p v-if="task.error" class="dl-drawer__error">{{ task.error }}</p>
            <div class="dl-drawer__actions">
              <n-button
                v-if="task.status === 'running'"
                size="tiny"
                :disabled="busy"
                @click="act(() => pauseDownloadTask(task.id!))"
              >
                暂停
              </n-button>
              <n-button
                v-if="task.status === 'paused'"
                size="tiny"
                :disabled="busy"
                @click="act(() => resumeDownloadTask(task.id!))"
              >
                恢复
              </n-button>
              <n-button
                v-if="task.status === 'queued' || task.status === 'running' || task.status === 'paused'"
                size="tiny"
                :disabled="busy"
                @click="act(() => cancelDownloadTask(task.id!))"
              >
                取消
              </n-button>
              <n-button
                v-if="task.status === 'done' && task.targetResourceId"
                size="tiny"
                type="primary"
                ghost
                @click="openResource(task.targetResourceId)"
              >
                查看
              </n-button>
            </div>
          </li>
        </ul>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NDrawer, NDrawerContent, NInput, NProgress, useMessage } from 'naive-ui'
import {
  cancelDownloadTask,
  createDownloadTask,
  invalidateResourceCache,
  listDownloadTasks,
  pauseDownloadTask,
  resumeDownloadTask,
} from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import { useSelectionStore } from '@/application/stores/selection'
import type { DownloadTask } from '@/domain'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ 'update:show': [boolean] }>()

const message = useMessage()
const router = useRouter()
const library = useLibraryStore()
const selection = useSelectionStore()
const url = ref('')
const busy = ref(false)
const tasks = ref<DownloadTask[]>([])
let timer: ReturnType<typeof setInterval> | undefined

const active = computed(() =>
  tasks.value.some((row) => row.status === 'queued' || row.status === 'running' || row.status === 'paused')
)

function onShow(value: boolean): void {
  emit('update:show', value)
}

async function refresh(): Promise<void> {
  try {
    tasks.value = await listDownloadTasks()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '无法读取下载任务')
  }
}

async function start(): Promise<void> {
  const raw = url.value.trim()
  if (!raw) {
    message.warning('请填写下载地址')
    return
  }
  busy.value = true
  try {
    await createDownloadTask(raw)
    url.value = ''
    await refresh()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '无法开始下载')
  } finally {
    busy.value = false
  }
}

async function act(run: () => Promise<DownloadTask>): Promise<void> {
  busy.value = true
  try {
    await run()
    await refresh()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    busy.value = false
  }
}

function openResource(id: number): void {
  invalidateResourceCache()
  library.bump('video')
  selection.select(id)
  void router.push('/video')
  emit('update:show', false)
}

function displayName(task: DownloadTask): string {
  return task.filename || task.url
}

function statusLabel(task: DownloadTask): string {
  if (task.status === 'queued') return '排队中'
  if (task.status === 'running') return '下载中'
  if (task.status === 'paused') return '已暂停'
  if (task.status === 'done') return '已完成'
  return '失败'
}

function percent(task: DownloadTask): number {
  if (!task.totalBytes) return 0
  return Math.min(100, Math.round((task.downloadedBytes / task.totalBytes) * 100))
}

function formatSpeed(speed: number): string {
  if (speed < 1024) return `${speed} B/s`
  if (speed < 1024 * 1024) return `${(speed / 1024).toFixed(1)} KB/s`
  return `${(speed / (1024 * 1024)).toFixed(1)} MB/s`
}

watch(
  () => [props.show, active.value] as const,
  ([open, on]) => {
    if (timer) {
      clearInterval(timer)
      timer = undefined
    }
    if (open) {
      void refresh()
      if (on) {
        timer = setInterval(() => {
          void refresh()
        }, 2000)
      }
    }
  }
)

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped lang="less">
.dl-drawer {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.dl-drawer__form {
  display: flex;
  gap: var(--sm-space-2);
  margin-bottom: var(--sm-space-3);
}

.dl-drawer__empty {
  color: var(--sm-color-text-muted);
  font-size: 13px;
}

.dl-drawer__list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: auto;
  min-height: 0;
}

.dl-drawer__item {
  padding: var(--sm-space-2) 0;
  border-bottom: 1px solid var(--sm-color-border);
}

.dl-drawer__name {
  font-size: 13px;
  word-break: break-all;
}

.dl-drawer__meta {
  font-size: 12px;
  color: var(--sm-color-text-muted);
  margin: 4px 0;
}

.dl-drawer__error {
  color: var(--sm-color-danger, #d03050);
  font-size: 12px;
  margin: 4px 0 0;
}

.dl-drawer__actions {
  display: flex;
  gap: var(--sm-space-2);
  margin-top: 6px;
}
</style>
