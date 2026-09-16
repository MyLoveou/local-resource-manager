/**
 * 资源类型展示名（首页卡片）。已启用类型走 RESOURCE_TYPE_LABEL。
 */
import { RESOURCE_TYPE_LABEL } from '@/domain/mediaTypes'

export const typeMap: Record<string, string> = {
  ...RESOURCE_TYPE_LABEL,
  audio: '音频',
  document: '文档',
  other: '其他',
}
