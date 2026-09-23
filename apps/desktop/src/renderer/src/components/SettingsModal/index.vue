<template>
  <n-modal :show="show" preset="card" title="设置" style="width: 640px" @update:show="onShow">
    <n-tabs type="line" animated>
      <n-tab-pane name="scrape" tab="刮削">
        <p v-if="view?.scrape.tmdb.envLocked" class="set-modal__hint">TMDB Key 由环境变量提供</p>
        <n-form-item label="TMDB API Key">
          <n-input
            v-model:value="tmdbKey"
            type="password"
            show-password-on="click"
            :disabled="busy || view?.scrape.tmdb.envLocked"
            :placeholder="tmdbPlaceholder"
          />
        </n-form-item>
        <p v-if="view?.scrape.bangumi.envLocked" class="set-modal__hint">Bangumi Token 由环境变量提供</p>
        <n-form-item label="Bangumi Token（可选）">
          <n-input
            v-model:value="bangumiToken"
            type="password"
            show-password-on="click"
            :disabled="busy || view?.scrape.bangumi.envLocked"
            :placeholder="bangumiPlaceholder"
          />
        </n-form-item>
        <p v-if="view?.scrape.mikan.envLocked" class="set-modal__hint">蜜柑地址由环境变量提供</p>
        <n-form-item label="蜜柑 Base URL">
          <n-input v-model:value="mikanUrl" :disabled="busy || view?.scrape.mikan.envLocked" />
        </n-form-item>
        <n-button size="small" type="primary" :loading="busy" @click="saveScrape">保存</n-button>
      </n-tab-pane>
      <n-tab-pane name="system" tab="系统">
        <p class="set-modal__about">后端 {{ view?.system.backendVersion ?? '—' }}</p>
        <div v-for="row in paths" :key="row.label" class="set-modal__path">
          <div>
            <div class="set-modal__label">{{ row.label }}</div>
            <div class="set-modal__value">{{ row.path }}</div>
          </div>
          <n-button size="tiny" :disabled="!row.path" @click="openDir(row.path)">打开</n-button>
        </div>
        <n-button size="small" type="primary" :loading="backing" @click="doBackup">立即备份</n-button>
      </n-tab-pane>
      <n-tab-pane name="consume" tab="消费渠道">
        <p class="set-modal__hint">自定义命令按空格拆成参数，{path} 单独成一段，不要加引号。例如：mpv {path}</p>
        <div v-for="row in channelRows" :key="row.type" class="set-modal__channel">
          <div class="set-modal__label">{{ row.label }}</div>
          <n-select
            size="small"
            :value="channels[row.type]?.mode"
            :options="row.modes"
            :disabled="busy"
            @update:value="(value: ChannelMode) => setMode(row.type, value)"
          />
          <n-input
            v-if="channels[row.type]?.mode === 'command'"
            size="small"
            :value="channels[row.type]?.command ?? ''"
            placeholder="程序 {path}"
            :disabled="busy"
            @update:value="(value: string) => setCommand(row.type, value)"
          />
        </div>
        <n-button size="small" type="primary" :loading="busy" @click="saveConsume">保存</n-button>
      </n-tab-pane>
    </n-tabs>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NFormItem, NInput, NModal, NSelect, NTabPane, NTabs, useMessage } from 'naive-ui'
import {
  backupLibrary,
  getSettings,
  patchConsumeSettings,
  patchScrapeSettings,
  type ChannelMode,
  type ChannelSetting,
  type SettingsView,
} from '@/infrastructure/http/settings'
import { TYPE_PROFILES } from '@/domain'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ 'update:show': [boolean] }>()

const message = useMessage()
const busy = ref(false)
const backing = ref(false)
const view = ref<SettingsView | null>(null)
const tmdbKey = ref('')
const bangumiToken = ref('')
const mikanUrl = ref('')
const channels = ref<Record<string, ChannelSetting>>({})

const MODE_LABEL: Record<ChannelMode, string> = {
  embedded: '内嵌预览',
  system: '系统默认',
  command: '自定义命令',
  workbench: '工作台',
}

const tmdbPlaceholder = computed(() =>
  view.value?.scrape.tmdb.configured ? `已配置 ${view.value.scrape.tmdb.hint ?? ''}`.trim() : '未配置'
)
const bangumiPlaceholder = computed(() =>
  view.value?.scrape.bangumi.configured ? `已配置 ${view.value.scrape.bangumi.hint ?? ''}`.trim() : '可选'
)

const channelRows = computed(() =>
  TYPE_PROFILES.map((profile) => {
    const modes: ChannelMode[] =
      profile.type === 'work_directory'
        ? ['workbench', 'system', 'command']
        : ['embedded', 'system', 'command']
    return {
      type: profile.type,
      label: profile.label,
      modes: modes.map((value) => ({ value, label: MODE_LABEL[value] })),
    }
  }),
)

const paths = computed(() => {
  const sys = view.value?.system
  if (!sys) return []
  return [
    { label: '数据库', path: sys.dbPath },
    { label: '资源库', path: sys.libraryPath },
    { label: '日志', path: sys.logDir },
    { label: '下载暂存', path: sys.downloadDir },
    { label: '备份', path: sys.backupDir },
  ]
})

function onShow(value: boolean): void {
  emit('update:show', value)
}

async function load(): Promise<void> {
  try {
    view.value = await getSettings()
    tmdbKey.value = ''
    bangumiToken.value = ''
    mikanUrl.value = view.value.scrape.mikan.baseUrl
    channels.value = { ...(view.value.consume?.channels ?? {}) }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '无法读取设置')
  }
}

async function saveScrape(): Promise<void> {
  const body: { tmdbApiKey?: string; bangumiAccessToken?: string; mikanBaseUrl?: string } = {}
  if (!view.value?.scrape.tmdb.envLocked && tmdbKey.value.trim()) {
    body.tmdbApiKey = tmdbKey.value.trim()
  }
  if (!view.value?.scrape.bangumi.envLocked && bangumiToken.value.trim()) {
    body.bangumiAccessToken = bangumiToken.value.trim()
  }
  if (!view.value?.scrape.mikan.envLocked) {
    body.mikanBaseUrl = mikanUrl.value.trim()
  }
  if (!Object.keys(body).length) {
    message.info('没有要保存的更改')
    return
  }
  busy.value = true
  try {
    view.value = await patchScrapeSettings(body)
    tmdbKey.value = ''
    bangumiToken.value = ''
    mikanUrl.value = view.value.scrape.mikan.baseUrl
    message.success('已保存')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    busy.value = false
  }
}

function setMode(type: string, mode: ChannelMode): void {
  const current = channels.value[type] ?? { mode, command: '' }
  channels.value = { ...channels.value, [type]: { ...current, mode } }
}

function setCommand(type: string, command: string): void {
  const current = channels.value[type] ?? { mode: 'command', command }
  channels.value = { ...channels.value, [type]: { ...current, command } }
}

async function saveConsume(): Promise<void> {
  busy.value = true
  try {
    view.value = await patchConsumeSettings({ channels: channels.value })
    channels.value = { ...(view.value.consume?.channels ?? {}) }
    message.success('已保存')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    busy.value = false
  }
}

async function openDir(path: string): Promise<void> {
  const api = window.electron
  if (!api?.openPath) {
    message.error('当前环境不能打开文件夹')
    return
  }
  const result = await api.openPath(path)
  if (!result.ok) message.error(result.message)
}

async function doBackup(): Promise<void> {
  backing.value = true
  try {
    const result = await backupLibrary()
    message.success(`已备份到 ${result.path}`)
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '备份失败')
  } finally {
    backing.value = false
  }
}

watch(
  () => props.show,
  (open) => {
    if (open) void load()
  }
)
</script>

<style scoped lang="less">
.set-modal__hint {
  font-size: 12px;
  color: var(--sm-color-text-muted);
  margin: 0 0 8px;
}

.set-modal__about {
  font-size: 13px;
  margin: 0 0 var(--sm-space-3);
}

.set-modal__path {
  display: flex;
  justify-content: space-between;
  gap: var(--sm-space-2);
  align-items: flex-start;
  margin-bottom: var(--sm-space-3);
}

.set-modal__label {
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.set-modal__value {
  font-size: 12px;
  word-break: break-all;
}

.set-modal__channel {
  display: grid;
  grid-template-columns: 72px 140px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}
</style>
