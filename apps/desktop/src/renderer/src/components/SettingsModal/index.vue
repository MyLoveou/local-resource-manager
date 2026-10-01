<template>
  <n-modal :show="show" preset="card" title="设置" style="width: 640px" @update:show="onShow">
    <n-tabs type="line" animated :value="activeTab" @update:value="activeTab = $event">
      <n-tab-pane name="scrape" tab="刮削">
        <p v-if="view?.scrape.tmdb.envLocked" class="set-modal__hint">TMDB Key 由环境变量提供</p>
        <n-form-item label="TMDB API Key">
          <n-input v-model:value="tmdbKey" type="password" show-password-on="click"
            :disabled="busy || view?.scrape.tmdb.envLocked" :placeholder="tmdbPlaceholder" />
        </n-form-item>
        <p v-if="view?.scrape.bangumi.envLocked" class="set-modal__hint">Bangumi Token 由环境变量提供</p>
        <n-form-item label="Bangumi Token（可选）">
          <n-input v-model:value="bangumiToken" type="password" show-password-on="click"
            :disabled="busy || view?.scrape.bangumi.envLocked" :placeholder="bangumiPlaceholder" />
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
          <div class="set-modal__path-head">
            <div class="set-modal__label">{{ row.label }}</div>
            <div class="set-modal__path-buttons">
              <n-button size="tiny" :disabled="!row.path" @click="openDir(row.path)">打开</n-button>
              <n-button size="tiny" type="primary" @click="changeSystemPath(row)">修改</n-button>
            </div>
          </div>
          <div class="set-modal__value">{{ row.path }}</div>
        </div>
        <n-button size="small" type="primary" :loading="backing" @click="doBackup">立即备份</n-button>
      </n-tab-pane>
      <n-tab-pane name="consume" tab="消费渠道">
        <p class="set-modal__hint">自定义命令按空格拆成参数，{path} 单独成一段，不要加引号。例如：mpv {path}</p>
        <div v-for="row in channelRows" :key="row.type" class="set-modal__channel">
          <div class="set-modal__label">{{ row.label }}</div>
          <n-select size="small" :value="channels[row.type]?.mode" :options="row.modes" :disabled="busy"
            @update:value="(value: ChannelMode) => setMode(row.type, value)" />
          <n-input v-if="channels[row.type]?.mode === 'command'" size="small" :value="channels[row.type]?.command ?? ''"
            placeholder="程序 {path}" :disabled="busy" @update:value="(value: string) => setCommand(row.type, value)" />
        </div>
        <n-button size="small" type="primary" :loading="busy" @click="saveConsume">保存</n-button>
      </n-tab-pane>
    </n-tabs>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NFormItem, NInput, NModal, NSelect, NTabPane, NTabs } from 'naive-ui'
import { notify } from '@/application/notify'
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
import { patchSystemSettings } from '@/infrastructure/http/settings'
import logger from '@/infrastructure/logging/logger'
import { SYSTEM_SETTING_PATH_MAP } from '@/static'
const props = defineProps<{ show: boolean; tab?: string }>()
const emit = defineEmits<{ 'update:show': [boolean] }>()

const activeTab = ref('scrape')
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
  return Object.entries(SYSTEM_SETTING_PATH_MAP).map(([key, label]) => ({
    key,
    label,
    path: sys[key as keyof SettingsView['system']],
  }))
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
    notify.fromError(error, { context: '读取设置' })
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
    notify.toast.info('没有要保存的更改')
    return
  }
  busy.value = true
  try {
    view.value = await patchScrapeSettings(body)
    tmdbKey.value = ''
    bangumiToken.value = ''
    mikanUrl.value = view.value.scrape.mikan.baseUrl
    notify.toast.success('已保存')
  } catch (error) {
    notify.fromError(error, { context: '保存刮削设置' })
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
    notify.toast.success('已保存')
  } catch (error) {
    notify.fromError(error, { context: '保存消费渠道' })
  } finally {
    busy.value = false
  }
}

async function openDir(path: string): Promise<void> {
  const api = window.electron
  if (!api?.openAny) {
    notify.toast.error('当前环境不能打开文件夹')
    return
  }
  const result = await api.openAny(path)
  if (!result.ok) notify.fromError(new Error(result.message), { context: '打开文件夹' })
}
async function changeSystemPath(item: { key: string; path: string, label: string }): Promise<void> {
  const api = window.electron
  if (!api?.selectDirectory) {
    notify.toast.error('当前环境不能选择文件夹')
    return
  }
  const result = await api.selectDirectory()
  logger.info('selectDirectory', result)
  // 用户取消选择不提示（设计 04 §2.4）
  if (!result) return
  logger.info('changeSystemPath', item.label, item.key, result)
  try {
    const body = {
      ...view.value?.system,
      [item.key]: result,
    }
    logger.info('changeSystemPath body', body)
    view.value = await patchSystemSettings(body as SettingsView['system'])
    logger.info('changeSystemPath view', view.value)
    notify.toast.success('已保存')
  } catch (error) {
    notify.fromError(error, { context: '保存系统路径' })
  }
}
async function doBackup(): Promise<void> {
  backing.value = true
  try {
    const result = await backupLibrary()
    notify.toast.success(`已备份到 ${result.path}`)
    await load()
  } catch (error) {
    notify.fromError(error, { context: '备份数据库' })
  } finally {
    backing.value = false
  }
}

watch(
  () => props.tab,
  (name) => {
    if (props.show && name) activeTab.value = name
  }
)

watch(
  () => props.show,
  (open) => {
    if (!open) return
    if (props.tab) activeTab.value = props.tab
    void load()
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
  flex-direction: column;
  gap: 6px;
  margin-bottom: var(--sm-space-3);
  padding-bottom: var(--sm-space-3);
  border-bottom: 1px solid var(--sm-color-border, rgba(0, 0, 0, 0.08));
}

.set-modal__path-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.set-modal__path-buttons {
  display: flex;
  flex-shrink: 0;
  gap: 6px;
}

.set-modal__label {
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.set-modal__value {
  font-size: 12px;
  line-height: 1.45;
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
