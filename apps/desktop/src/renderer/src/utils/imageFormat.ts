/** 查看器里用原生 img 播动图；Viewer.js 画布会停在第一帧。 */
export function isAnimatedImageFormat(format?: string | null): boolean {
  const value = (format ?? '').toLowerCase().replace(/^\./, '')
  return value === 'gif' || value === 'webp'
}

/** Chromium 通常解不开，失败时引导外部应用。仍先尝试加载。 */
export function isLikelyUnsupportedInlineFormat(format?: string | null): boolean {
  const value = (format ?? '').toLowerCase().replace(/^\./, '')
  return value === 'heic' || value === 'heif'
}
