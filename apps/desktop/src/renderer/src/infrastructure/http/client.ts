/**
 * axios 实例（基础设施层 · HTTP 传输）
 * baseURL 由 Electron 主进程注入（preload），开发态默认兜底 127.0.0.1:8000
 */
import axios from 'axios'
import { logger } from '../logging/logger'

/** 开发态默认后端地址（后端绑定 127.0.0.1:8000） */
const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: window.electron?.backend?.baseUrl ?? DEFAULT_BASE_URL,
  timeout: 10000,
})

/** 请求拦截：注入 token 鉴权头 */
client.interceptors.request.use((config) => {
  const token = window.electron?.backend?.token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 响应拦截：失败写入日志（不记录 token） */
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const method = error.config?.method?.toUpperCase() ?? '?'
    const url = error.config?.url ?? '?'
    const status = error.response?.status ?? 'network'
    logger.warn(`[http] ${method} ${url} -> ${status}`)
    return Promise.reject(error)
  }
)

export default client
