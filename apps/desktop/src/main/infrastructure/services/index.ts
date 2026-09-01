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

export async function stopServices(): Promise<void> {
  if (backend) { await backend.stop(); backend = null }
}