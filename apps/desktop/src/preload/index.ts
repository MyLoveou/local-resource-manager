import { contextBridge } from 'electron'

/**
 * preload：渲染进程与主进程的安全桥。
 * 领域/业务能力通过 contextBridge 暴露（后续：IPC 调用后端服务）。
 */
const api = {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node
  }
}

contextBridge.exposeInMainWorld('electron', api)

export type ElectronApi = typeof api
