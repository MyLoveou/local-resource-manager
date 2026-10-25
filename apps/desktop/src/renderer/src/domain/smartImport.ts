/**
 * 智能导入：建议与置信分档（与后端 repositories_suggestions.HIGH_CONFIDENCE 对齐）。
 */

/** 高置信：默认勾选，可一键采纳。 */
export const HIGH_CONFIDENCE = 0.85

/** 中置信：展示但不勾选。低于此值折叠提示。 */
export const MID_CONFIDENCE = 0.5

export interface SuggestionGroup {
  field: string
  value: Record<string, unknown> | null
  source: string
  confidence: number
  count: number
  reasons: string[]
  suggestionIds: number[]
  sampleResourceIds: number[]
}

export interface SuggestionPage {
  groups: SuggestionGroup[]
  total: number
}

export interface SuggestionSummary {
  pending: number
  highConfidence: number
  jobs: number
}

export interface SuggestionGroupKey {
  field: string
  value: Record<string, unknown> | null
}

export interface SuggestionApplyRequest {
  ids?: number[]
  groups?: SuggestionGroupKey[]
  minConfidence?: number
}

export interface SuggestionApplyResult {
  accepted: number
  skipped: number
  updatedResources: number
}

export interface SuggestionRejectRequest {
  ids?: number[]
  groups?: SuggestionGroupKey[]
  all?: boolean
}

export interface SuggestionRejectResult {
  rejected: number
}

export type ConfidenceTier = 'high' | 'mid' | 'low'

export function confidenceTier(confidence: number): ConfidenceTier {
  if (confidence >= HIGH_CONFIDENCE) return 'high'
  if (confidence >= MID_CONFIDENCE) return 'mid'
  return 'low'
}

/** 分组显示用的主语：目前只有 title（text），分类在 S2 用 name。 */
export function suggestionLabel(group: SuggestionGroup): string {
  const value = group.value ?? {}
  const text = typeof value.text === 'string' ? value.text : ''
  if (text) return text
  const name = typeof value.name === 'string' ? value.name : ''
  return name || group.field
}

/** 分组键：同一 (field, value) 视为一组，用于勾选与批量操作。 */
export function groupKey(group: SuggestionGroup): string {
  return `${group.field}::${JSON.stringify(group.value ?? null)}`
}
