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

type AppNotifyPayload = {
  level: 'success' | 'info' | 'warning' | 'error'
  title: string
  description?: string
  duration?: number
}

type UpdateStatus = {
  phase:
    | 'idle'
    | 'checking'
    | 'available'
    | 'downloading'
    | 'downloaded'
    | 'up-to-date'
    | 'error'
    | 'unsupported'
  currentVersion: string
  version?: string
  releaseNotes?: string
  percent?: number
  transferred?: number
  total?: number
  bytesPerSecond?: number
  message?: string
}

let pendingNotify: AppNotifyPayload | null = null
let handlerRef: ((payload: AppNotifyPayload) => void) | null = null

ipcRenderer.on('app:notify', (_event, payload: AppNotifyPayload) => {
  pendingNotify = payload
  handlerRef?.(payload)
})

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
  selectDirectory: (): Promise<string | null> => ipcRenderer.invoke('dialog:selectDirectory'),
  showItemInFolder: (path: string): Promise<{ ok: true; canceled?: boolean } | { ok: false; message: string }> =>
    ipcRenderer.invoke('shell:showItemInFolder', { path }),
  openPath: (path: string): Promise<{ ok: true; canceled?: boolean } | { ok: false; message: string }> =>
    ipcRenderer.invoke('shell:openPath', { path }),
  openWith: (path: string): Promise<{ ok: true; canceled?: boolean } | { ok: false; message: string }> =>
    ipcRenderer.invoke('shell:openWith', { path }),
  openAny: (path: string): Promise<{ ok: true; canceled?: boolean } | { ok: false; message: string }> =>
    ipcRenderer.invoke('shell:openAny', { path }),
  openExternal: (url: string): Promise<{ ok: true; canceled?: boolean } | { ok: false; message: string }> =>
    ipcRenderer.invoke('shell:openExternal', { url }),
  runCommand: (payload: {
    template: string
    path: string
  }): Promise<{ ok: true } | { ok: false; message: string }> => ipcRenderer.invoke('shell:runCommand', payload),
  selectThemeCss: (): Promise<string | null> => ipcRenderer.invoke('dialog:selectThemeCss'),
  readThemeCss: (path: string): Promise<{ ok: true; css: string } | { ok: false; message: string }> =>
    ipcRenderer.invoke('theme:readCss', path),
  onAppNotify: (
    handler: (payload: {
      level: 'success' | 'info' | 'warning' | 'error'
      title: string
      description?: string
      duration?: number
    }) => void
  ): void => {
    handlerRef = handler
    if (pendingNotify) handler(pendingNotify)
  },
  update: {
    getState: (): Promise<UpdateStatus> => ipcRenderer.invoke('update:get-state'),
    check: (): Promise<UpdateStatus> => ipcRenderer.invoke('update:check'),
    download: (): Promise<UpdateStatus> => ipcRenderer.invoke('update:download'),
    install: (): void => {
      void ipcRenderer.invoke('update:install')
    },
    onStatus: (handler: (status: UpdateStatus) => void): (() => void) => {
      const listener = (_event: unknown, status: UpdateStatus): void => handler(status)
      ipcRenderer.on('update:status', listener)
      return () => ipcRenderer.removeListener('update:status', listener)
    },
  },
}

contextBridge.exposeInMainWorld('electron', api)

export type ElectronApi = typeof api
