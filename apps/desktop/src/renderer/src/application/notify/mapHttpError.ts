import type { MappedError } from '@/domain/notify'

const SENSITIVE = /bearer\s+\S+|token[=:]\s*\S+/gi

function clip(text: string): string {
  const clean = text.replace(SENSITIVE, '***').trim()
  return clean.length > 200 ? `${clean.slice(0, 200)}…` : clean
}

function detailText(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null
  const row = data as Record<string, unknown>
  const detail = row.detail
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: unknown }).msg)
        return ''
      })
      .filter(Boolean)
    if (parts.length) return parts.join('；')
  }
  if (typeof row.message === 'string' && row.message.trim() && row.message !== 'ok') {
    return row.message.trim()
  }
  return null
}

interface HttpLike {
  code?: string
  message?: string
  response?: { status?: number; data?: unknown }
}

function asHttp(error: unknown): HttpLike | null {
  if (error == null || typeof error !== 'object') return null
  const row = error as HttpLike
  if (row.response || row.code || typeof row.message === 'string') return row
  return null
}

export function mapHttpError(error: unknown, context = '操作'): MappedError {
  const title = `${context}失败`
  const http = asHttp(error)
  if (http) {
    const timedOut = http.code === 'ECONNABORTED' || /timeout/i.test(http.message ?? '')
    if (timedOut) {
      return { title, description: '请求超时，请稍后重试', level: 'error' }
    }
    if (!http.response) {
      return { title, description: '无法连接后端服务，请确认应用已正常启动', level: 'error' }
    }
    const status = http.response.status ?? 0
    const detail = detailText(http.response.data)
    if (detail) return { title, description: clip(detail), level: 'error' }
    if (status === 401 || status === 403) {
      return { title, description: '无访问权限', level: 'error' }
    }
    if (status === 404) {
      return { title, description: '请求的资源不存在', level: 'error' }
    }
    if (status >= 500) {
      return { title, description: '服务异常，请查看日志或稍后重试', level: 'error' }
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return { title, description: clip(error.message), level: 'error' }
  }
  return { title, description: '发生未知错误', level: 'error' }
}
