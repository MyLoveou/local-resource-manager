/**
 * 领域类型统一出口（barrel）
 * 引用方式：import { Resource } from '@/domain'
 */
export * from './resource'
export * from './mediaTypes'
export type { TypeProfile, ConsumeKind, IngestKind, StorageKind } from './libraryTypes'
export { TYPE_PROFILES, SHARED_SORT_KEYS, SORT_LABELS, allowedSortKeys } from './libraryTypes'
export * from './mediaLabels'
export * from './scrape'
export * from './settings'
export * from './overview'
export * from './collection'
export * from './category'
export * from './savedView'
export * from './workspace'
export * from './photo'
export * from './update'
export * from './constants'
