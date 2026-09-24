/**
 * 第二次点击的消费路由：渠道设置优先于类型默认。
 * workbench 只留下选中态；command 由主进程按空格拆词，{path} 单独成参，不经过 shell。
 */
import { notify } from '@/application/notify'
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
import { PlayerByConsume } from '@/static'

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

export async function consumeResource(item: Resource, playlist: number[]): Promise<void> {
  if (item.id == null) return
  const row = await getResource(item.id)
  if (row.id == null) return
  const channels = await getConsumeChannels()
  const configured = channels[row.type]
  const mode = configured?.mode ?? DEFAULT_MODE[row.type]
  const command = configured?.command ?? ''
  const kind = consumeKindOf(row.type)
  if (mode === 'embedded' && (kind == null || kind === 'overlay-series')) return
  void postConsumption(row.id, mode).catch(() => undefined)
  if (mode === 'workbench') return
  if (mode === 'command') {
    const path = launchOrPrimaryPath(row)
    if (!path) {
      fail('找不到文件')
      return
    }
    if (!command.includes('{path}')) {
      fail('命令须包含 {path}', true)
      return
    }
    const api = window.electron
    if (!api?.runCommand) {
      fail('当前环境不能执行命令')
      return
    }
    const result = await api.runCommand({ template: command, path })
    if (!result.ok) fail(result.message || '找不到命令', true)
    return
  }
  if (mode === 'system') {
    const message = await openAny(row)
    if (message) fail(message)
    return
  }
  if (kind == null || kind === 'overlay-series') return
  if (kind === 'shell-open') {
    const message = await openAny(row)
    if (message) fail(message)
    return
  }
  if (kind === 'overlay-model') {
    const format = (row.files?.find((file) => file.role === FILE_ROLE.PRIMARY)?.format ?? '').toLowerCase()
    if ((MODEL_PREVIEW_EXTENSIONS as readonly string[]).includes(format)) {
      PlayerByConsume[kind].open(row.id, playlist)
      return
    }
    const message = await openLaunchOrPrimary(row)
    if (message) fail(message)
    return
  }
  PlayerByConsume[kind].open(row.id, playlist)
}
