import { contextBridge, ipcRenderer } from 'electron'
/** 在 contextIsolation 下把 __electronLog 桥到渲染进程，配合主进程 log.initialize() */
import 'electron-log/preload'

/**
 * preload：渲染进程与主进程的安全桥。
 * backend 地址/token 由主进程通过 additionalArguments 注入（比 process.env 可靠）。
 */

/** 从 process.argv 读取主进程注入的 `--name=value` 参数 */
function readArg(name: string): string | undefined {
  const prefix = `--${name}=`
  const arg = process.argv.find((a) => a.startsWith(prefix))
  return arg?.slice(prefix.length)
}

const api = {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node
  },
  backend: {
    baseUrl: readArg('backend-url') ?? process.env.BACKEND_URL ?? 'http://127.0.0.1:8000',
    token: readArg('backend-token') ?? process.env.BACKEND_TOKEN ?? ''
  },
  selectFiles: (filters?: { name: string; extensions: string[] }[]): Promise<string[]> =>
    ipcRenderer.invoke('dialog:selectFiles', filters),
  selectDirectory: (): Promise<string | null> => ipcRenderer.invoke('dialog:selectDirectory')
}

contextBridge.exposeInMainWorld('electron', api)

export type ElectronApi = typeof api
