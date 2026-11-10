/** 提示词工作台 HTTP 客户端 */
import client from './client'

export interface PromptLibrary {
  models: Record<string, { name: string; prefix?: string; negative?: string; params?: Record<string, unknown> }>
  categories: { id: string; name: string; icon: string; tags: { en: string; zh: string }[] }[]
  characters: { game: string; name: string; tag: string; charZh: string; auto: string }[]
  presets: { name: string; desc: string; cat: string; tags: { en: string; zh: string }[] }[]
  templates: { id: string; name: string; desc: string; tags: { en: string; zh: string }[] }[]
  danbooru?: { en: string; zh: string; count: number; aliases: string[]; nsfw: boolean; cat: string }[]
  rules: Record<string, unknown>
  pinyin: Record<string, string>
}

export interface PromptSave {
  id: number
  title: string
  model: string
  positive: string
  negative: string
  note?: string | null
  params?: Record<string, unknown> | null
  categories?: string[] | null
  favorite: boolean
  image_data?: string | null
  created_at: string
  updated_at: string
}

export async function getPromptLibrary(): Promise<PromptLibrary> {
  const { data } = await client.get<PromptLibrary>('/prompts/library')
  return data
}

export async function getPromptSettings(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>('/prompts/settings')
  return data
}

export async function putPromptSettings(values: Record<string, unknown>): Promise<void> {
  await client.put('/prompts/settings', values)
}

export async function listPromptSaves(params: { q?: string; tag?: string; favorite?: boolean } = {}) {
  const { data } = await client.get<{ items: PromptSave[] }>('/prompts/saves', { params })
  return data.items
}

export async function createPromptSave(body: {
  title: string
  model: string
  positive: string
  negative: string
  note?: string
  params?: Record<string, unknown>
  favorite?: boolean
  tags?: string[]
  image_data?: string
}): Promise<{ id: number }> {
  const { data } = await client.post<{ id: number }>('/prompts/saves', body)
  return data
}

export async function deletePromptSave(id: number): Promise<void> {
  await client.delete(`/prompts/saves/${id}`)
}

export async function patchPromptSave(
  id: number,
  body: Record<string, unknown>,
): Promise<void> {
  await client.patch(`/prompts/saves/${id}`, body)
}

export async function addPromptHistory(body: {
  model: string
  positive: string
  negative: string
  saveId?: number | null
}): Promise<void> {
  await client.post('/prompts/history', body)
}

export async function exportPrompts(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>('/prompts/export')
  return data
}

export async function importPrompts(payload: Record<string, unknown>): Promise<{
  saves: number
  customTags: number
  customPresets: number
  skipped: number
}> {
  const { data } = await client.post('/prompts/import', payload)
  return data
}
