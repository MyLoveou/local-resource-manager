import { useVideoPlayerStore } from "@/application/stores/videoPlayer"
import { useImageViewerStore } from "@/application/stores/imageViewer"
import { useAudioPlayerStore } from "@/application/stores/audioPlayer"
import { useModelPreviewStore } from "@/application/stores/modelPreview"
import type { ConsumeKind } from "@/domain/libraryTypes"

const videoPlayer = useVideoPlayerStore()
const imageViewer = useImageViewerStore()
const audioPlayer = useAudioPlayerStore()
const modelPreview = useModelPreviewStore()

export const NextAndPre = {
  video: {
    prev: '上一集',
    next: '下一集',
  },
  image: {
    prev: '上一张',
    next: '下一张',
  }
}

export const PlayerByConsume: Record<
  ConsumeKind,
  { open: (id: number, ids: number[]) => void; close: () => void; prev?: () => void; next?: () => void }
> = {
  'overlay-video': {
    close: videoPlayer.close,
    open: (id, ids) => videoPlayer.open(id, ids),
  },
  'overlay-image': {
    close: imageViewer.close,
    open: imageViewer.open,
    prev: imageViewer.prev,
    next: imageViewer.next,
  },
  'overlay-audio': {
    close: audioPlayer.close,
    open: audioPlayer.open,
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

/** @deprecated 用 PlayerByConsume[consumeKind] */
export const Player = {
  video: PlayerByConsume['overlay-video'],
  image: PlayerByConsume['overlay-image'],
}
