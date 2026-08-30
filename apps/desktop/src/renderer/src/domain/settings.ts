/**
 * 设置与适配器类型（与后端 OpenAPI 契约对齐）
 * 后端对应：apps/backend/app/shared/models.py
 */
import type { AdapterKey } from './constants'

/** 应用设置（KV 结构） */
export interface SettingsEntry {
  key: string
  value: Record<string, unknown>
}

/** 站点适配器配置（插件式） */
export interface SiteAdapter {
  id?: number
  key: AdapterKey
  enabled: boolean
  config: Record<string, unknown>
}
