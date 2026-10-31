import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { useAudioPlayerStore } from '@/application/stores/audioPlayer'
import { useModelPreviewStore } from '@/application/stores/modelPreview'
import type { ConsumeKind } from '@/domain/libraryTypes'
import type { AudioPlayerPager } from '@/application/stores/audioPlayer'
import type { ImageViewerPager } from '@/application/stores/imageViewer'
type PlayerApi = {
  open: (id: number, ids: number[], fileId?: number | null) => void
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
      open: (id, ids, fileId) => videoPlayer.open(id, ids, fileId),
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
      // 系列（番剧/AV）复用视频播放器：选集点击带 fileId 打开对应集
      close: videoPlayer.close,
      open: (id, ids, fileId) => videoPlayer.open(id, ids, fileId),
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
