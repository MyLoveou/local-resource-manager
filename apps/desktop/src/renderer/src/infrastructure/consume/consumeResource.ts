/**
 * 资源打开命令：页面只传资源与播放上下文，渠道/类型/播放器在这里统一分发。
 * 这不是数据失效广播；打开是有调用方的命令，不能全局广播。
 */
import { notify } from '@/application/notify'
import type { AudioPlayerPager } from '@/application/stores/audioPlayer'
import type { ImageViewerPager } from '@/application/stores/imageViewer'
import {
  consumeKindOf,
  FILE_ROLE,
  MODEL_PREVIEW_EXTENSIONS,
  type Resource,
  type ResourceType,
} from '@/domain'
import { getResource } from '@/infrastructure/http'
import { postConsumption } from '@/infrastructure/http/workbench'
import { getConsumeChannels, type ChannelMode } from '@/infrastructure/http/settings'
import { launchOrPrimaryPath, openAny, openLaunchOrPrimary } from '@/infrastructure/shell/openLibraryFile'
import { PlayerByConsume } from './players'

const DEFAULT_MODE: Record<ResourceType, ChannelMode> = {
  image: 'embedded',
  video: 'embedded',
  anime: 'embedded',
  av: 'embedded',
  audio: 'embedded',
  model: 'embedded',
  novel: 'system',
  comic: 'system',
  game: 'system',
  work_directory: 'workbench',
}

export type OpenableResource = Pick<Resource, 'id' | 'type'>

export type ResourceOpenOptions = {
  /** 查看器/播放器可前后切换的 ID 列表；不传则只打开当前项 */
  playlist?: number[]
  /** 视频分集：打开指定文件 */
  fileId?: number | null
  /** 图片查看器/音频播放器的翻页器 */
  pager?: ImageViewerPager | AudioPlayerPager | null
}

function fail(description: string, offerSettings = false): void {
  notify.push({
    level: 'error',
    title: '无法打开',
    description,
    action: offerSettings
      ? {
          label: '配置打开方式',
          onClick: () => window.dispatchEvent(new CustomEvent('sm:open-settings', { detail: 'consume' })),
        }
      : undefined,
  })
}

export async function openResource(
  item: OpenableResource,
  options: ResourceOpenOptions = {},
): Promise<boolean> {
  if (item.id == null) return false
  const row = await getResource(item.id)
  if (row.id == null) return false
  const channels = await getConsumeChannels()
  const configured = channels[row.type]
  const mode = configured?.mode ?? DEFAULT_MODE[row.type]
  const command = configured?.command ?? ''
  const kind = consumeKindOf(row.type)
  const playlist = options.playlist?.length ? options.playlist : [row.id]
  // 系列必须带具体集；只拿到作品卡时给出可执行提示，而不是静默失败
  const seriesNeedsFile = kind === 'overlay-series' && options.fileId == null
  if (mode === 'embedded' && (kind == null || seriesNeedsFile)) {
    if (seriesNeedsFile) fail('请从选集里选择一集播放')
    return false
  }
  void postConsumption(row.id, mode).catch(() => undefined)
  if (mode === 'workbench') return false
  if (mode === 'command') {
    const path = launchOrPrimaryPath(row)
    if (!path) {
      fail('找不到文件')
      return false
    }
    if (!command.includes('{path}')) {
      fail('命令须包含 {path}', true)
      return false
    }
    const api = window.electron
    if (!api?.runCommand) {
      fail('当前环境不能执行命令')
      return false
    }
    const result = await api.runCommand({ template: command, path })
    if (!result.ok) fail(result.message || '找不到命令', true)
    return result.ok
  }
  if (mode === 'system') {
    const message = await openAny(row)
    if (message) fail(message)
    return !message
  }
  if (kind == null || seriesNeedsFile) return false
  if (kind === 'shell-open') {
    const message = await openAny(row)
    if (message) fail(message)
    return !message
  }
  if (options.pager && (kind === 'overlay-image' || kind === 'overlay-audio')) {
    PlayerByConsume[kind].bindPager?.(options.pager)
  }
  if (kind === 'overlay-model') {
    const format = (row.files?.find((file) => file.role === FILE_ROLE.PRIMARY)?.format ?? '').toLowerCase()
    if ((MODEL_PREVIEW_EXTENSIONS as readonly string[]).includes(format)) {
      PlayerByConsume[kind].open(row.id, playlist, options.fileId)
      return true
    }
    const message = await openLaunchOrPrimary(row)
    if (message) fail(message)
    return !message
  }
  PlayerByConsume[kind].open(row.id, playlist, options.fileId)
  return true
}
