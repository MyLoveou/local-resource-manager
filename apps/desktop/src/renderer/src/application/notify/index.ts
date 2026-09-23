import type { ConfirmOptions, FromErrorOptions, MappedError, PushOptions } from '@/domain/notify'
import { logger } from '@/infrastructure/logging/logger'
import { NButton } from 'naive-ui'
import { h } from 'vue'
import { getDiscrete, initNotify } from './discrete'
import { mapHttpError } from './mapHttpError'

export { initNotify }

const recent = new Map<string, number>()

function deduped(key: string): boolean {
  const now = Date.now()
  const last = recent.get(key) ?? 0
  if (now - last < 1000) return true
  recent.set(key, now)
  return false
}

function toast(level: 'success' | 'info' | 'warning' | 'error', content: string): void {
  const { message } = getDiscrete()
  const duration = level === 'error' ? 5000 : 3000
  message[level](content, { duration })
}

export const notify = {
  toast: {
    success: (content: string) => toast('success', content),
    info: (content: string) => toast('info', content),
    warning: (content: string) => toast('warning', content),
    error: (content: string) => toast('error', content),
  },
  push(options: PushOptions): void {
    const key = options.key ?? `${options.level}|${options.title}|${options.description ?? ''}`
    if (deduped(key)) return
    const { notification } = getDiscrete()
    const duration = options.duration ?? 4500
    notification[options.level]({
      title: options.title,
      content: options.description,
      duration,
      action: options.action
        ? () =>
            h(
              NButton,
              {
                size: 'small',
                type: 'primary',
                onClick: () => options.action?.onClick?.(),
              },
              { default: () => options.action?.label ?? '' }
            )
        : undefined,
    })
  },
  confirm(options: ConfirmOptions): Promise<boolean> {
    const { dialog } = getDiscrete()
    const level = options.level ?? 'warning'
    const type = level === 'error' ? 'error' : level === 'default' ? 'info' : 'warning'
    return new Promise((resolve) => {
      let settled = false
      const done = (value: boolean): void => {
        if (settled) return
        settled = true
        resolve(value)
      }
      dialog[type]({
        title: options.title,
        content: options.content,
        positiveText: options.positiveText ?? '确定',
        negativeText: options.negativeText ?? '取消',
        positiveButtonProps: level === 'error' ? { type: 'error' } : undefined,
        onPositiveClick: () => done(true),
        onNegativeClick: () => done(false),
        onClose: () => done(false),
      })
    })
  },
  loading: {
    start: () => getDiscrete().loadingBar.start(),
    finish: () => getDiscrete().loadingBar.finish(),
    error: () => getDiscrete().loadingBar.error(),
  },
  fromError(error: unknown, options?: FromErrorOptions): MappedError {
    const mapped = mapHttpError(error, options?.context ?? '操作')
    logger.debug('[notify] %s', error instanceof Error ? error.message : String(error))
    if (options?.silent) return mapped
    const description = mapped.description ?? ''
    const usePush = Boolean(options?.asPush) || description.length > 40
    if (usePush) {
      notify.push({
        level: mapped.level ?? 'error',
        title: mapped.title,
        description,
        duration: 4500,
      })
    } else {
      toast('error', description || mapped.title)
    }
    return mapped
  },
}
