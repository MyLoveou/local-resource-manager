/** 下一张：已加载范围内，或列表还有后续页。 */
export function canGoNext(
  index: number,
  length: number,
  hasMore: boolean,
  loadingMore: boolean
): boolean {
  if (index < 0) return false
  if (index < length - 1) return true
  return hasMore || loadingMore
}
