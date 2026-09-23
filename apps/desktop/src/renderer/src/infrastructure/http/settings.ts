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

function rememberChannels(view: SettingsView): SettingsView {
  channelCache = view.consume?.channels ?? {}
  return view
}

export async function getSettings(): Promise<SettingsView> {
  const { data } = await client.get<SettingsView>('/settings')
  return rememberChannels(data)
}

export async function getConsumeChannels(): Promise<Record<string, ChannelSetting>> {
  if (channelCache) return channelCache
  const view = await getSettings()
  return view.consume?.channels ?? {}
}

export async function patchScrapeSettings(body: ScrapeSettingsPatch): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/scrape', body)
  return data
}

export async function patchConsumeSettings(body: {
  channels: Record<string, ChannelSetting>
}): Promise<SettingsView> {
  const { data } = await client.patch<SettingsView>('/settings/consume', body)
  return rememberChannels(data)
}

export async function backupLibrary(): Promise<BackupResult> {
  const { data } = await client.post<BackupResult>('/settings/backup')
  return data
}
