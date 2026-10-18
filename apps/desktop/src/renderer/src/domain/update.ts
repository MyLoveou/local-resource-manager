/** 应用更新状态（与主进程 update.ts / preload 对齐） */
export type UpdatePhase =
  | 'idle'
  | 'checking'
  | 'available'
  | 'downloading'
  | 'downloaded'
  | 'up-to-date'
  | 'error'
  | 'unsupported'

export interface UpdateStatus {
  phase: UpdatePhase
  currentVersion: string
  version?: string
  releaseNotes?: string
  percent?: number
  message?: string
}
