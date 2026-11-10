/** 提示词存档的导出/导入：与界面无关，便于复用与测试。 */
import { exportPrompts, importPrompts } from '@/infrastructure/http/prompts'

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
