/**
 * axios 实例（基础设施层 · HTTP 传输）
 * baseURL 由 Electron 主进程注入（preload），开发态默认兜底 127.0.0.1:8000
 */
import axios, { AxiosError } from 'axios'
import { API_CODE_OK, API_STATUS_ERROR, API_STATUS_SUCCESS } from '@/domain'
import { logger } from '../logging/logger'

/** 开发态默认后端地址（后端绑定 127.0.0.1:8000） */
const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

export interface ApiEnvelope<T = unknown> {
  code: number
  status: string
  message: string
  data: T
}

function isEnvelope(payload: unknown): payload is ApiEnvelope {
  if (payload == null || typeof payload !== 'object') return false
  if (typeof Blob !== 'undefined' && payload instanceof Blob) return false
  if (payload instanceof ArrayBuffer) return false
  const row = payload as Record<string, unknown>
  return (
    typeof row.code === 'number' &&
    (row.status === API_STATUS_SUCCESS || row.status === API_STATUS_ERROR) &&
    typeof row.message === 'string' &&
    'data' in row
  )
}

const client = axios.create({
  baseURL: window.electron?.backend?.baseUrl ?? DEFAULT_BASE_URL,
  timeout: 10000,
  // 数组参数序列化为重复键（tagIds=1&tagIds=2），FastAPI 的 list[int] Query 才能解析；
  // 默认的 tagIds[]=1 形式会被静默丢弃，导致标签筛选不生效
  paramsSerializer: { indexes: null },
})

/** 请求拦截：注入 token 鉴权头 */
client.interceptors.request.use((config) => {
  const token = window.electron?.backend?.token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 响应拦截：解开信封，业务层只拿到 data */
client.interceptors.response.use(
  (response) => {
    const responseType = response.config.responseType
    if (responseType === 'blob' || responseType === 'arraybuffer') {
      return response
    }
    logger.debug('Response: %s %s -> %s', response.config.method, response.config.url, response.status)
    const payload = response.data
    if (isEnvelope(payload)) {
      if (payload.status !== API_STATUS_SUCCESS || payload.code !== API_CODE_OK) {
        return Promise.reject(
          new AxiosError(
            payload.message || 'request failed',
            AxiosError.ERR_BAD_RESPONSE,
            response.config,
            response.request,
            response
          )
        )
      }
      response.data = payload.data
    }
    return response
  },
  (error) => {
    const method = error.config?.method?.toUpperCase() ?? '?'
    const url = error.config?.url ?? '?'
    const status = error.response?.status ?? 'network'
    logger.warn(`[http] ${method} ${url} -> ${status}`)
    const payload = error.response?.data
    if (isEnvelope(payload) && payload.message) {
      error.message = payload.message
    }
    return Promise.reject(error)
  }
)

export default client
