/** 提示词存档的导出/导入：与界面无关，便于复用与测试。 */
import {
  exportPromptLibrary,
  exportPrompts,
  importPromptLibrary,
  importPrompts,
} from '@/infrastructure/http/prompts'

export interface ImportResult {
  saves: number
  customTags: number
  customPresets: number
  skipped: number
}

export async function downloadBackup(): Promise<number> {
  const payload = await exportPrompts()
  const blob = new Blob([JSON.stringify(payload, null, 1)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `prompts-${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(url)
  return Array.isArray(payload.saves) ? payload.saves.length : 0
}

export async function importBackup(file: File): Promise<ImportResult> {
  const text = await file.text()
  const payload = JSON.parse(text) as Record<string, unknown>
  return importPrompts(payload)
}

/** 下载内置库（安装包不带数据时用它补给） */
export async function downloadLibrary(): Promise<number> {
  const payload = await exportPromptLibrary()
  const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `prompt-library-${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(url)
  const categories = Array.isArray(payload.categories) ? payload.categories.length : 0
  const danbooru = Array.isArray(payload.danbooru) ? payload.danbooru.length : 0
  return categories + danbooru
}

export async function importLibrary(file: File): Promise<string> {
  const text = await file.text()
  const payload = JSON.parse(text) as Record<string, unknown>
  const result = await importPromptLibrary(payload)
  return `内置库已导入：分类 ${result.categories} · 角色 ${result.characters} · 预设 ${result.presets} · 模板 ${result.templates} · Danbooru ${result.danbooru}`
}
