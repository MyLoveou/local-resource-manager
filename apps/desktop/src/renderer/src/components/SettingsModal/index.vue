<template>
  <n-modal
    :show="show"
    preset="card"
    title="设置"
    style="width: 640px"
    @update:show="onShow"
  >
    <n-tabs
      type="line"
      animated
      :value="activeTab"
      @update:value="activeTab = $event"
    >
      <n-tab-pane
        name="scrape"
        tab="刮削"
      >
        <p
          v-if="view?.scrape.tmdb.envLocked"
          class="set-modal__hint"
        >
          TMDB Key 由环境变量提供
        </p>
        <n-form-item label="TMDB API Key">
          <n-input
            v-model:value="tmdbKey"
            type="password"
            show-password-on="click"
            :disabled="busy || view?.scrape.tmdb.envLocked"
            :placeholder="tmdbPlaceholder"
          />
        </n-form-item>
        <p
          v-if="view?.scrape.bangumi.envLocked"
          class="set-modal__hint"
        >
          Bangumi Token 由环境变量提供
        </p>
        <n-form-item label="Bangumi Token（可选）">
          <n-input
            v-model:value="bangumiToken"
            type="password"
            show-password-on="click"
            :disabled="busy || view?.scrape.bangumi.envLocked"
            :placeholder="bangumiPlaceholder"
          />
        </n-form-item>
        <p
          v-if="view?.scrape.mikan.envLocked"
          class="set-modal__hint"
        >
          蜜柑地址由环境变量提供
        </p>
        <n-form-item label="蜜柑 Base URL">
          <n-input
            v-model:value="mikanUrl"
            :disabled="busy || view?.scrape.mikan.envLocked"
          />
        </n-form-item>
        <n-button
          size="small"
          type="primary"
          :loading="busy"
          @click="saveScrape"
        >
          保存
        </n-button>
      </n-tab-pane>
      <n-tab-pane
        name="system"
        tab="系统"
      >
        <p class="set-modal__about">
          后端 {{ view?.system.backendVersion ?? '—' }}
        </p>
        <div
          v-for="row in paths"
          :key="row.label"
          class="set-modal__path"
        >
          <div class="set-modal__path-head">
            <div class="set-modal__label">
              {{ row.label }}
            </div>
            <div class="set-modal__path-buttons">
              <n-button
                size="tiny"
                :disabled="!row.path"
                @click="openDir(row.path)"
              >
                打开
              </n-button>
              <n-button
                size="tiny"
                type="primary"
                @click="changeSystemPath(row)"
              >
                修改
              </n-button>
            </div>
          </div>
          <div class="set-modal__value">
            {{ row.path }}
          </div>
        </div>
        <p class="set-modal__hint">
          资源库路径仅在空库时允许修改；已有资源请先备份/迁移。
        </p>
        <div class="set-modal__backup-target">
          <span>备份位置：{{ view?.system.backupDir || '—' }}</span>
          <n-button
            size="tiny"
            @click="changeSystemPath({ key: 'backupDir', label: '备份', path: view?.system.backupDir ?? '' })"
          >
            更改
          </n-button>
        </div>
        <div class="set-modal__actions">
          <n-button
            size="small"
            type="primary"
            :loading="backing"
            @click="doBackup"
          >
            备份库和图片
          </n-button>
          <n-button
            size="small"
            :loading="thumbRepairing"
            @click="doRepairThumbnails"
          >
            重建缩略图
          </n-button>
          <n-button
            size="small"
            :loading="restoring"
            @click="doRestore"
          >
            恢复备份
          </n-button>
        </div>
        <p class="set-modal__hint">
          恢复会先校验备份，然后重启应用替换当前数据库和图片。
        </p>
      </n-tab-pane>
      <n-tab-pane
        name="consume"
        tab="消费渠道"
      >
        <p class="set-modal__hint">
          自定义命令按空格拆成参数，{path} 单独成一段，不要加引号。例如：mpv {path}
        </p>
        <div
          v-for="row in channelRows"
          :key="row.type"
          class="set-modal__channel"
        >
          <div class="set-modal__label">
            {{ row.label }}
          </div>
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
        <n-button
          size="small"
          type="primary"
          :loading="busy"
          @click="saveConsume"
        >
          保存
        </n-button>
      </n-tab-pane>
      <n-tab-pane
        name="watch"
        tab="监视目录"
      >
        <p
          v-if="watchEnvLocked"
          class="set-modal__hint"
        >
          监视目录由环境变量提供，不能在此修改
        </p>
        <p
          v-else
          class="set-modal__hint"
        >
          按资源类型监视源目录，目录内新增文件会自动进入对应类型。保存后立即生效。
        </p>
        <div
          v-for="row in watchRows"
          :key="row.type"
          class="set-modal__watch"
        >
          <div class="set-modal__watch-head">
            <div class="set-modal__label">
              {{ row.label }}
            </div>
            <n-button
              size="tiny"
              :disabled="busy || watchEnvLocked"
              @click="addWatchDir(row.type)"
            >
              添加目录
            </n-button>
          </div>
          <div class="set-modal__watch-tags">
            <n-tag
              v-for="dir in watchDirs[row.type] ?? []"
              :key="dir"
              closable
              size="small"
              :disabled="busy || watchEnvLocked"
              @close="removeWatchDir(row.type, dir)"
            >
              {{ dir }}
            </n-tag>
            <span
              v-if="!(watchDirs[row.type]?.length)"
              class="set-modal__watch-empty"
            >未监视</span>
          </div>
        </div>
        <n-button
          size="small"
          type="primary"
          :loading="busy"
          :disabled="watchEnvLocked"
          @click="saveWatch"
        >
          保存
        </n-button>
      </n-tab-pane>
      <n-tab-pane
        name="parse"
        tab="命名解析"
      >
        <p class="set-modal__hint">
          每行一条正则，命名组：title / author / bv / ep / date。用户规则优先于内置 bilidown 规则；不匹配时按文件名原样导入。文件名带 BV 的视频会自动获取元数据。
        </p>
        <n-input
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 12 }"
          :value="parseRulesText"
          placeholder="^(?P<ep>\d+)-UP (?P<author>.+?)-(?P<bv>BV1[0-9A-Za-z]{9})-(?P<date>\d{4}-\d{1,2}-\d{1,2})-(?P<title>.+)$"
          :disabled="busy"
          @update:value="parseRulesText = $event"
        />
        <div class="set-modal__parse-switches">
          <n-switch
            :value="parseTitleWithEp"
            :disabled="busy"
            @update:value="parseTitleWithEp = $event"
          />
          <span>标题带 EP 前缀（43. 标题）</span>
        </div>
        <div class="set-modal__parse-switches">
          <n-switch
            :value="parseAutoCollection"
            :disabled="busy"
            @update:value="parseAutoCollection = $event"
          />
          <span>监视视频自动归集合集（按目录名）</span>
        </div>
        <n-button
          size="small"
          type="primary"
          :loading="busy"
          @click="saveParse"
        >
          保存
        </n-button>
      </n-tab-pane>
      <n-tab-pane
        name="update"
        tab="更新"
      >
        <p class="set-modal__hint">
          当前版本：{{ update.status.currentVersion || '—' }}
        </p>
        <p class="set-modal__hint">
          状态：{{ updatePhaseLabel }}
        </p>
        <n-progress
          v-if="update.status.phase === 'downloading'"
          type="line"
          :percentage="update.status.percent ?? 0"
          :height="6"
        />
        <p
          v-if="update.status.phase === 'downloading'"
          class="set-modal__progress"
        >
          {{ updateProgressDetail }}
        </p>
        <pre
          v-if="update.status.releaseNotes"
          class="set-modal__notes"
        >{{ update.status.releaseNotes }}</pre>
        <div class="set-modal__parse-switches">
          <n-button
            size="small"
            :loading="update.status.phase === 'checking'"
            @click="checkUpdate"
          >
            检查更新
          </n-button>
          <n-button
            v-if="update.status.phase === 'available'"
            size="small"
            type="primary"
            @click="update.download()"
          >
            下载更新
          </n-button>
          <n-button
            v-if="update.status.phase === 'downloaded'"
            size="small"
            type="primary"
            @click="update.install()"
          >
            重启安装
          </n-button>
          <n-button
            v-if="showManualDownload"
            size="small"
            quaternary
            @click="openReleasePage"
          >
            手动下载
          </n-button>
        </div>
        <p class="set-modal__hint set-modal__speed-tip">
          自动下载走 GitHub，速度受网络影响；较慢时可手动下载安装包。
        </p>
      </n-tab-pane>
    </n-tabs>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NFormItem, NInput, NModal, NProgress, NSelect, NSwitch, NTabPane, NTabs, NTag } from 'naive-ui'
import { notify } from '@/application/notify'
import {
  backupLibrary,
  getSettings,
  patchConsumeSettings,
  patchParseSettings,
  patchScrapeSettings,
  patchWatchSettings,
  prepareRestore,
  type ChannelMode,
  type ChannelSetting,
  type SettingsView,
} from '@/infrastructure/http/settings'
import { TYPE_PROFILES } from '@/domain'
import { patchSystemSettings } from '@/infrastructure/http/settings'
import { backfillThumbnails } from '@/infrastructure/http/photos'
import logger from '@/infrastructure/logging/logger'
import { useUpdateStore } from '@/application/stores/update'
import { SYSTEM_SETTING_PATH_MAP } from '@/static'
const props = defineProps<{ show: boolean; tab?: string }>()
const update = useUpdateStore()
const updatePhaseLabel = computed(() => {
  const status = update.status
  switch (status.phase) {
    case 'idle':
      return '未检查'
    case 'checking':
      return '检查中…'
    case 'available':
      return `发现新版本 ${status.version ?? ''}`
    case 'downloading':
      return `下载中 ${status.percent ?? 0}%`
    case 'downloaded':
      return '已下载，待重启安装'
    case 'up-to-date':
      return '已是最新版本'
    case 'error':
      return status.message || '更新失败'
    case 'unsupported':
      return status.message || '仅安装版支持自动更新'
    default:
      return status.phase
  }
})

const RELEASE_PAGE = 'https://github.com/MyLoveou/local-resource-manager/releases/latest'

function formatBytes(value = 0): string {
  if (value <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  const size = value / 1024 ** index
  return `${size >= 100 || index === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[index]}`
}

function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

const updateProgressDetail = computed(() => {
  const { transferred, total, bytesPerSecond } = update.status
  if (!transferred) return '连接中…'
  const parts = [`${formatBytes(transferred)}${total ? ` / ${formatBytes(total)}` : ''}`]
  if (bytesPerSecond && bytesPerSecond > 0) {
    parts.push(`${formatBytes(bytesPerSecond)}/s`)
    if (total && total > transferred) {
      parts.push(`剩余约 ${formatDuration((total - transferred) / bytesPerSecond)}`)
    }
  }
  return parts.join(' · ')
})

const showManualDownload = computed(() =>
  ['available', 'downloading', 'error', 'unsupported'].includes(update.status.phase)
)

async function checkUpdate(): Promise<void> {
  try {
    await update.check()
    if (update.status.phase === 'unsupported') {
      notify.toast.warning(update.status.message || '当前版本不支持自动更新，请手动下载')
    }
  } catch (error) {
    notify.fromError(error, { context: '检查更新' })
  }
}

async function openReleasePage(): Promise<void> {
  const api = window.electron
  if (!api?.openExternal) {
    notify.toast.error('当前环境不支持打开浏览器')
    return
  }
  const result = await api.openExternal(RELEASE_PAGE)
  if (!result.ok) notify.toast.error(result.message)
}

void update.init()
const emit = defineEmits<{ 'update:show': [boolean] }>()

const activeTab = ref('scrape')
const busy = ref(false)
const backing = ref(false)
const thumbRepairing = ref(false)
const restoring = ref(false)
const view = ref<SettingsView | null>(null)
const tmdbKey = ref('')
const bangumiToken = ref('')
const mikanUrl = ref('')
const channels = ref<Record<string, ChannelSetting>>({})
const watchDirs = ref<Record<string, string[]>>({})
const parseRulesText = ref('')
const parseTitleWithEp = ref(false)
const parseAutoCollection = ref(false)

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

// 可监视类型 = 有扩展名映射且非 package 型（与后端 File_Extension_Map/WATCHABLE_TYPES 对齐）
const watchRows = computed(() =>
  TYPE_PROFILES.filter((profile) => profile.extensions.length > 0 && profile.ingestKind !== 'package').map(
    (profile) => ({
      type: profile.type,
      label: profile.label,
    }),
  ),
)

const watchEnvLocked = computed(() => view.value?.watch.envLocked ?? false)

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
    watchDirs.value = { ...(view.value.watch?.dirs ?? {}) }
    parseRulesText.value = (view.value.parse?.rules ?? []).join('\n')
    parseTitleWithEp.value = view.value.parse?.titleWithEp ?? false
    parseAutoCollection.value = view.value.parse?.autoCollection ?? false
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

async function addWatchDir(type: string): Promise<void> {
  const api = window.electron
  if (!api?.selectDirectory) {
    notify.toast.error('当前环境不能选择文件夹')
    return
  }
  const result = await api.selectDirectory()
  // 用户取消选择不提示
  if (!result) return
  const current = watchDirs.value[type] ?? []
  if (current.includes(result)) {
    notify.toast.info('该目录已在监视列表中')
    return
  }
  watchDirs.value = { ...watchDirs.value, [type]: [...current, result] }
}

function removeWatchDir(type: string, dir: string): void {
  const current = watchDirs.value[type] ?? []
  watchDirs.value = { ...watchDirs.value, [type]: current.filter((item) => item !== dir) }
}

async function saveWatch(): Promise<void> {
  busy.value = true
  try {
    view.value = await patchWatchSettings({ dirs: watchDirs.value })
    watchDirs.value = { ...(view.value.watch?.dirs ?? {}) }
    notify.toast.success('已保存，监视已生效')
  } catch (error) {
    notify.fromError(error, { context: '保存监视目录' })
  } finally {
    busy.value = false
  }
}

async function saveParse(): Promise<void> {
  const rules = parseRulesText.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
  busy.value = true
  try {
    view.value = await patchParseSettings({
      rules,
      titleWithEp: parseTitleWithEp.value,
      autoCollection: parseAutoCollection.value,
    })
    parseRulesText.value = (view.value.parse?.rules ?? []).join('\n')
    notify.toast.success('已保存')
  } catch (error) {
    notify.fromError(error, { context: '保存命名解析规则' })
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
    notify.fromError(error, { context: '备份资源库' })
  } finally {
    backing.value = false
  }
}

async function doRepairThumbnails(): Promise<void> {
  if (!window.confirm('将重建图片缩略图，照片较多时可能需要几分钟。继续？')) return
  thumbRepairing.value = true
  try {
    const result = await backfillThumbnails(true)
    notify.toast.success(
      `缩略图完成：修复 ${result.repaired}，跳过 ${result.skipped}，失败 ${result.failed}`,
    )
  } catch (error) {
    notify.fromError(error, { context: '重建缩略图' })
  } finally {
    thumbRepairing.value = false
  }
}

async function doRestore(): Promise<void> {
  const files = await window.electron?.selectFiles([
    { name: '资源管理器备份', extensions: ['zip'] },
  ])
  const path = files?.[0]
  if (!path) return
  if (!window.confirm('恢复会替换当前数据库和图片，并在完成后重启应用。继续？')) return
  restoring.value = true
  try {
    await prepareRestore(path)
    notify.toast.success('备份已校验，应用即将重启并恢复')
    if (window.electron?.relaunch) {
      await window.electron.relaunch()
    } else {
      notify.toast.warning('请手动重启应用以完成恢复')
    }
  } catch (error) {
    notify.fromError(error, { context: '准备恢复备份' })
  } finally {
    restoring.value = false
  }
}

watch(
  [() => props.show, () => props.tab],
  ([open, tab]) => {
    if (open && tab) activeTab.value = tab
    if (open) void load()
  },
  { immediate: true },
)
</script>

<style scoped lang="less">
.set-modal__hint {
  font-size: 12px;
  color: var(--sm-color-text-muted);
  margin: 0 0 8px;
}

.set-modal__notes {
  max-height: 220px;
  overflow: auto;
  margin: 8px 0;
  padding: 8px;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 12px;
  color: var(--sm-color-text-muted);
  background: var(--sm-color-bg-surface);
  border-radius: var(--sm-radius-control);
}

.set-modal__progress {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.set-modal__speed-tip {
  margin-top: 8px;
  margin-bottom: 0;
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

.set-modal__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.set-modal__backup-target {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
  word-break: break-all;
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

.set-modal__watch {
  margin-bottom: 14px;
}

.set-modal__watch-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.set-modal__watch-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.set-modal__watch-empty {
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.set-modal__parse-switches {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0;
  font-size: 13px;
}
</style>
