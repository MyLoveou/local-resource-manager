/** 判断 img 原生播放的格式；WebP 需要再检查是否真的带动画。 */
export function isAnimatedImageFormat(format?: string | null): boolean {
  const value = (format ?? '').toLowerCase().replace(/^\./, '')
  return value === 'gif' || value === 'webp'
}

export function isWebpFormat(format?: string | null): boolean {
  return (format ?? '').toLowerCase().replace(/^\./, '') === 'webp'
}

/** 读取 WebP 文件头，判断是否包含 ANIM/ANMF 动画块。 */
export function webpBytesAreAnimated(data: ArrayBuffer): boolean {
  const bytes = new Uint8Array(data)
  if (bytes.length < 12) return false
  const ascii = (start: number, length: number): string =>
    String.fromCharCode(...bytes.subarray(start, start + length))
  if (ascii(0, 4) !== 'RIFF' || ascii(8, 4) !== 'WEBP') return false
  const limit = Math.min(bytes.length - 4, 64 * 1024)
  for (let index = 12; index <= limit; index += 1) {
    const chunk = ascii(index, 4)
    if (chunk === 'ANIM' || chunk === 'ANMF') return true
  }
  return false
}

export async function webpUrlIsAnimated(url: string): Promise<boolean | null> {
  if (!url) return false
  try {
    const response = await fetch(url, { headers: { Range: 'bytes=0-65535' } })
    if (!response.ok && response.status !== 206) return null
    return webpBytesAreAnimated(await response.arrayBuffer())
  } catch {
    return null
  }
}

/** Chromium 通常解不开，失败时引导外部应用。仍先尝试加载。 */
export function isLikelyUnsupportedInlineFormat(format?: string | null): boolean {
  const value = (format ?? '').toLowerCase().replace(/^\./, '')
  return value === 'heic' || value === 'heif'
}
