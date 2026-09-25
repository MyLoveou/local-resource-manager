import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { useAudioPlayerStore } from '@/application/stores/audioPlayer'
import { useModelPreviewStore } from '@/application/stores/modelPreview'
import type { ConsumeKind } from '@/domain/libraryTypes'
import type { AudioPlayerPager } from '@/application/stores/audioPlayer'
import type { ImageViewerPager } from '@/application/stores/imageViewer'
type PlayerApi = {
  open: (id: number, ids: number[]) => void
  close: () => void
  prev?: () => void
  next?: () => void
  bindPager?: (pager: AudioPlayerPager | ImageViewerPager) => void
  unbindPager?: () => void
}

function playerByConsume(): Record<ConsumeKind, PlayerApi> {
  const videoPlayer = useVideoPlayerStore()
  const imageViewer = useImageViewerStore()
  const audioPlayer = useAudioPlayerStore()
  const modelPreview = useModelPreviewStore()
  return {
    'overlay-video': {
      close: videoPlayer.close,
      open: (id, ids) => videoPlayer.open(id, ids),
    },
    'overlay-image': {
      close: imageViewer.close,
      open: imageViewer.open,
      prev: imageViewer.prev,
      next: imageViewer.next,
      bindPager: imageViewer.bindPager,
      unbindPager: imageViewer.unbindPager,
    },
    'overlay-audio': {
      close: audioPlayer.close,
      open: audioPlayer.open,
      prev: audioPlayer.prev,
      next: audioPlayer.next,
      bindPager: audioPlayer.bindPager,
      unbindPager: audioPlayer.unbindPager,
    },
    'overlay-model': {
      close: modelPreview.close,
      open: modelPreview.open,
    },
    'overlay-series': {
      close: () => undefined,
      open: () => undefined,
    },
    'shell-open': {
      close: () => undefined,
      open: () => undefined,
    },
  }
}

export const PlayerByConsume: Record<ConsumeKind, PlayerApi> = new Proxy({} as Record<ConsumeKind, PlayerApi>, {
  get(_target, key: string) {
    return playerByConsume()[key as ConsumeKind]
  },
})
