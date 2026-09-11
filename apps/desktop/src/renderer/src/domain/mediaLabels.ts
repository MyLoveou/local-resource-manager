/** 清晰度 / 画质展示（与后端 media_labels 对齐；阈值查表，禁止散落字面量） */

const CLARITY_STANDARD: Record<string, string> = {
  '7680x4320': '8K',
  '4320x7680': '8K',
  '3840x2160': '4K',
  '2160x3840': '4K',
  '2560x1440': '1440p',
  '1440x2560': '1440p',
  '1920x1080': '1080p',
  '1080x1920': '1080p',
  '1280x720': '720p',
  '720x1280': '720p',
  '854x480': '480p',
  '480x854': '480p',
}

const CLARITY_SHORT_SIDE: [number, string][] = [
  [2160, '4K'],
  [1440, '1440p'],
  [1080, '1080p'],
  [720, '720p'],
  [480, '480p'],
]

const EFFICIENT_CODECS = ['hevc', 'h265', 'hev1', 'hvc1', 'av1', 'av01', 'vp9', 'vp09'] as const
const EFFICIENT_CODEC_BPP_WEIGHT = 1.6

const QUALITY_BPP_LABELS: [number, string][] = [
  [0.2, '高'],
  [0.1, '中'],
  [0.05, '一般'],
]
const QUALITY_BPP_FALLBACK = '偏低'

const EMPTY_LABEL = '—'
const BITRATE_MBPS = 1_000_000
const BITRATE_KBPS = 1_000

export function clarityLabel(width?: number | null, height?: number | null): string {
  if (
    width == null ||
    height == null ||
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    width <= 0 ||
    height <= 0
  ) {
    return EMPTY_LABEL
  }
  const pair = CLARITY_STANDARD[`${width}x${height}`]
  if (pair) return pair
  const short = Math.min(width, height)
  for (const [threshold, label] of CLARITY_SHORT_SIDE) {
    if (short >= threshold) return label
  }
  return `${short}p`
}

export function qualityLabel(
  width?: number | null,
  height?: number | null,
  fps?: number | null,
  bitrate?: number | null,
  codec?: string | null
): string {
  if (
    width == null ||
    height == null ||
    fps == null ||
    bitrate == null ||
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    !Number.isFinite(fps) ||
    !Number.isFinite(bitrate) ||
    width <= 0 ||
    height <= 0 ||
    fps <= 0 ||
    bitrate <= 0
  ) {
    return EMPTY_LABEL
  }
  let bpp = bitrate / (width * height * fps)
  const name = (codec ?? '').toLowerCase().split('.')[0]
  if ((EFFICIENT_CODECS as readonly string[]).includes(name)) bpp *= EFFICIENT_CODEC_BPP_WEIGHT
  for (const [threshold, label] of QUALITY_BPP_LABELS) {
    if (bpp >= threshold) return label
  }
  return QUALITY_BPP_FALLBACK
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null || seconds < 0 || Number.isNaN(seconds)) return EMPTY_LABEL
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

export function formatFps(fps?: number | null): string {
  if (fps == null || fps <= 0) return EMPTY_LABEL
  const rounded = Math.round(fps * 100) / 100
  return Number.isInteger(rounded) ? `${rounded} fps` : `${rounded.toFixed(2)} fps`
}

export function formatBitrate(bps?: number | null): string {
  if (bps == null || bps <= 0) return EMPTY_LABEL
  if (bps >= BITRATE_MBPS) return `${(bps / BITRATE_MBPS).toFixed(1)} Mbps`
  if (bps >= BITRATE_KBPS) return `${(bps / BITRATE_KBPS).toFixed(0)} kbps`
  return `${bps} bps`
}

export function formatResolution(width?: number | null, height?: number | null): string {
  if (width == null || height == null || width <= 0 || height <= 0) return EMPTY_LABEL
  return `${width}×${height}`
}
