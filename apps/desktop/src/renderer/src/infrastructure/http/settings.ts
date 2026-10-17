/**
 * 设置端点（/settings）
 */
import client from './client'

export interface SecretState {
  configured: boolean
  hint?: string | null
  envLocked: boolean
}

export interface MikanState {
  baseUrl: string
  envLocked: boolean
}

export type ChannelMode = 'embedded' | 'system' | 'command' | 'workbench'

export interface ChannelSetting {
  mode: ChannelMode
  command: string
}

export interface SettingsView {
  scrape: {
    tmdb: SecretState
    bangumi: SecretState
    mikan: MikanState
  }
  system: {
    dbPath: string
    libraryPath: string
    logDir: string
    downloadDir: string
    backupDir: string
    backendVersion: string
  }
  consume: {
    channels: Record<string, ChannelSetting>
  }
  watch: {
    dirs: Record<string, string[]>
    envLocked: boolean
  }
  parse: {
    rules: string[]
    titleWithEp: boolean
    autoCollection: boolean
  }
}

export interface ScrapeSettingsPatch {
  tmdbApiKey?: string
  bangumiAccessToken?: string
  mikanBaseUrl?: string
}

export interface BackupResult {
  path: string
}

let channelCache: Record<string, ChannelSetting> | null = null
/** 记住消费渠道设置 */
function rememberChannels(view: SettingsView): SettingsView {
  channelCache = view.consume?.channels ?? {}
  return view
}
/**
 * 获取设置
 * @returns SettingsView
 */
export async function getSettings(): Promise<SettingsView> {
  const { data } = await client.get<SettingsView>('/settings')
  return rememberChannels(data)
}

/**
 * 获取消费渠道设置
 * @returns Record<string, ChannelSetting>
 */
export async function getConsumeChannels(): Promise<Record<string, ChannelSetting>> {
  if (channelCache) return channelCache
  const view = await getSettings()
  return view.consume?.channels ?? {}
}
/**
 * 更新刮削设置
 * @param body 
 * @returns 
 */
export async function patchScrapeSettings(body: ScrapeSettingsPatch): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/scrape', body)
  return data
}

/**
 * 更新消费渠道设置
 * @param body 消费渠道设置
 * @returns SettingsView
 */
export async function patchConsumeSettings(body: {
  channels: Record<string, ChannelSetting>
}): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/consume', body)
  return rememberChannels(data)
}

/**
 * 备份库
 * @returns BackupResult
 */
export async function backupLibrary(): Promise<BackupResult> {
  const { data } = await client.post<BackupResult>('/settings/backup')
  return data
}


/**
 * 更新系统设置
 */

export async function patchSystemSettings(body: SettingsView['system']): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/system', body)
  return data
}

/**
 * 更新监视目录设置（保存后后端即时重配监视器）
 * @param body 监视目录
 * @returns SettingsView
 */
export async function patchWatchSettings(body: {
  dirs: Record<string, string[]>
}): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/watch', body)
  return data
}

/**
 * 更新视频文件名解析规则（每行一条正则，命名组 title/author/bv/ep/date）
 * @param body 规则列表
 * @returns SettingsView
 */
export async function patchParseSettings(body: {
  rules?: string[]
  titleWithEp?: boolean
  autoCollection?: boolean
}): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/parse', body)
  return data
}