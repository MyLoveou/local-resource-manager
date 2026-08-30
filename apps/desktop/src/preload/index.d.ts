import type { ElectronApi } from './index'

declare global {
  interface Window {
    electron: ElectronApi
  }
}

export {}
