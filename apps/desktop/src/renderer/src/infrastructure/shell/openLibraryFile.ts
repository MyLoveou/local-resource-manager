/**
 * 打开库内副本或登记的源路径：所在位置 / 默认应用 / 选择其他应用。
 */
import type { Resource } from '@/domain'
import { launchOrPrimaryPath, revealablePath } from './revealPath'

export { launchOrPrimaryPath, revealablePath }

export function primaryLocalPath(resource: Resource | null | undefined): string | null {
  return launchOrPrimaryPath(resource)
}

export async function revealInFolder(resource: Resource | null | undefined): Promise<string | null> {
  const path = revealablePath(resource)
  if (!path) return '找不到可定位的文件'
  const api = window.electron
  if (!api?.showItemInFolder) return '当前环境不能打开文件夹'
  const result = await api.showItemInFolder(path)
  return result.ok ? null : result.message
}

export async function openAny(resource: Resource | null | undefined): Promise<string | null> {
  const path = primaryLocalPath(resource)
  if (!path) return '找不到库内文件'
  const api = window.electron
  if (!api?.openAny) return '当前环境不能打开外部应用'
  const result = await api.openAny(path)
  return result.ok ? null : result.message
}

export async function openPrimaryDefault(resource: Resource | null | undefined): Promise<string | null> {
  const path = primaryLocalPath(resource)
  if (!path) return '找不到库内文件'
  const api = window.electron
  if (!api?.openPath) return '当前环境不能打开外部应用'
  const result = await api.openPath(path)
  return result.ok ? null : result.message
}

export async function openLaunchOrPrimary(resource: Resource | null | undefined): Promise<string | null> {
  return openPrimaryDefault(resource)
}

export async function openPrimaryWithOther(resource: Resource | null | undefined): Promise<string | null> {
  const path = primaryLocalPath(resource)
  if (!path) return '找不到库内文件'
  const api = window.electron
  if (!api?.openWith) return '当前环境不能选择应用'
  const result = await api.openWith(path)
  if (result.ok) return null
  return result.message
}
