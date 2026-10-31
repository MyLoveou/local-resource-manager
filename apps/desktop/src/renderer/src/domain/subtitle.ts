/** 字幕轨与格式转换（播放器与信息栏共用）。 */

export interface SubtitleTrack {
  id: number
  episodeId?: number | null
  url: string
  label: string
  language?: string | null
  /** 浏览器 <track> 能否直接使用；ass/ssa 需要 libass 渲染 */
  renderable: boolean
  format?: string | null
}

const SRT_TIME = /(\d{2}:\d{2}:\d{2}),(\d{3})/g

/** SRT → WebVTT：加头部、时间轴逗号改点，其余原样保留。 */
export function srtToVtt(input: string): string {
  const body = input
    .replace(/^\uFEFF/, '')
    .replace(/\r\n/g, '\n')
    .replace(SRT_TIME, '$1.$2')
  if (body.startsWith('WEBVTT')) return body
  return `WEBVTT\n\n${body}`
}

export function subtitleLabel(track: SubtitleTrack): string {
  const parts = [track.language || '', track.label || ''].filter(Boolean)
  return parts.join(' · ') || `字幕 ${track.id}`
}
