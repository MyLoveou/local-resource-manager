import { BackendInstance } from "./backend"
import { startBackend } from "./backend"
import { loadBackendConfig } from "./config"
let backend: BackendInstance | null = null

export async function startServices(): Promise<BackendInstance> {
  backend = await startBackend(loadBackendConfig())
  process.env.BACKEND_URL = backend.baseURL     // ← 唯一赋值点
  process.env.BACKEND_TOKEN = backend.token
  return backend
}

export async function restartServices(): Promise<BackendInstance> {
  const previous = backend
  await stopServices()
  // 先尝试沿用原端口与 token：这样渲染进程手里的地址继续有效，不必重开窗口
  try {
    backend = await startBackend(loadBackendConfig(), {
      port: previous?.port,
      token: previous?.token,
    })
  } catch {
    backend = await startBackend(loadBackendConfig())
  }
  process.env.BACKEND_URL = backend.baseURL
  process.env.BACKEND_TOKEN = backend.token
  return backend
}

export async function stopServices(): Promise<void> {
  if (backend) { await backend.stop(); backend = null }
}