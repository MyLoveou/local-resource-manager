/**
 * ass/ssa 字幕渲染：libass-wasm（Jellyfin 的 SubtitlesOctopus）。
 *
 * 只在这一种场景使用——srt/vtt 走原生 <track>，不需要 wasm。
 * 渲染器会自己拉取字幕 URL，所以必须是带签名的地址。
 */

import SubtitlesOctopus from '@jellyfin/libass-wasm'
import workerUrl from '@jellyfin/libass-wasm/dist/js/subtitles-octopus-worker.js?url'
import legacyWorkerUrl from '@jellyfin/libass-wasm/dist/js/subtitles-octopus-worker-legacy.js?url'
import wasmUrl from '@jellyfin/libass-wasm/dist/js/subtitles-octopus-worker.wasm?url'
import fontUrl from '@jellyfin/libass-wasm/dist/js/default.woff2?url'

let instance: SubtitlesOctopus | null = null

export function destroyAssOverlay(): void {
  if (!instance) return
  try {
    instance.destroy()
  } catch {
    // 卸载失败不该影响播放器
  }
  instance = null
}

export function mountAssOverlay(video: HTMLVideoElement, subUrl: string): void {
  destroyAssOverlay()
  instance = new SubtitlesOctopus({
    video,
    subUrl,
    workerUrl,
    legacyWorkerUrl,
    wasmUrl,
    renderMode: 'wasm',
    fonts: ['default.woff2'],
    availableFonts: { 'default.woff2': fontUrl },
  })
}
