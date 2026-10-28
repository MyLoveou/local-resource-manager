declare module '@jellyfin/libass-wasm' {
  /** libass-wasm（SubtitlesOctopus）没有自带类型，按最小可用接口声明 */
  export default class SubtitlesOctopus {
    constructor(options: {
      video: HTMLVideoElement
      subUrl: string
      workerUrl: string
      legacyWorkerUrl?: string
      wasmUrl?: string
      fonts?: string[]
      availableFonts?: Record<string, string>
      renderMode?: 'wasm' | 'js'
      onReady?: () => void
      onError?: (error: unknown) => void
    })
    destroy(): void
  }
}
