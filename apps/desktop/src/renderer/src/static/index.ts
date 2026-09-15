import { useVideoPlayerStore } from "@/application/stores/videoPlayer"
import { useImageViewerStore } from "@/application/stores/imageViewer"
const videoPlayer = useVideoPlayerStore()
const imageViewer = useImageViewerStore()
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

export const Player = {
  video: {
    close: videoPlayer.close,
    open: videoPlayer.open,
  },
  image: {
    close: imageViewer.close,
    open: imageViewer.open,
    prev: imageViewer.prev,
    next: imageViewer.next,
  }
}