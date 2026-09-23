/** 提示级别 */
export type NotifyLevel = 'success' | 'info' | 'warning' | 'error'

export interface PromptAction {
  label: string
  onClick?: () => void
  actionId?: string
}

export interface PushOptions {
  level: NotifyLevel
  title: string
  description?: string
  duration?: number
  action?: PromptAction
  key?: string
}

export interface ConfirmOptions {
  title: string
  content: string
  level?: 'default' | 'warning' | 'error'
  positiveText?: string
  negativeText?: string
}

export interface FromErrorOptions {
  context?: string
  silent?: boolean
  asPush?: boolean
}

export interface MappedError {
  title: string
  description?: string
  level?: NotifyLevel
}

/** 主进程 → 渲染，不含函数 */
export interface PushPayload {
  level: NotifyLevel
  title: string
  description?: string
  duration?: number
  actionId?: string
}
