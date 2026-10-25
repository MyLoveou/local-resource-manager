/**
 * 播放进度（video-management S1）。
 *
 * 阈值与后端 `application/progress.py` 保持一致：
 * 低于 MIN_RECORD_SECONDS 不记，达到 COMPLETE_RATIO 视为看完。
 */

/** 低于这个秒数不写进度（避免误点产生噪音）。 */
export const MIN_RECORD_SECONDS = 10

/** 达到这个比例视为看完，下次从头开始。 */
export const COMPLETE_RATIO = 0.95

/** 播放中两次上报的最小间隔（秒）。 */
export const PROGRESS_REPORT_INTERVAL_SECONDS = 5

export interface PlaybackProgress {
  fileId: number
  resourceId: number
  position: number
  duration: number | null
  completed: boolean
  updatedAt: string | null
}

export interface PlaybackProgressInput {
  fileId: number
  position: number
  duration?: number | null
}

export interface ResumeItem {
  resourceId: number
  fileId: number
  title: string
  type: string
  coverPath: string | null
  position: number
  duration: number | null
  percent: number
  seasonNumber: number | null
  episodeNumber: number | null
  updatedAt: string | null
}

export interface ResumePage {
  items: ResumeItem[]
  total: number
}
