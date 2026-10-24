/** 应用更新状态（主进程 electron-updater 的渲染侧单例） */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { UpdateStatus } from '@/domain'

export const useUpdateStore = defineStore('update', () => {
  const status = ref<UpdateStatus>({ phase: 'idle', currentVersion: '' })
  let unsubscribe: (() => void) | null = null

  async function init(): Promise<void> {
    const api = window.electron?.update
    if (!api) return
    if (!unsubscribe) {
      unsubscribe = api.onStatus((next) => {
        status.value = next
      })
    }
    status.value = await api.getState()
  }

  async function check(): Promise<void> {
    const api = window.electron?.update
    if (!api) return
    status.value = await api.check()
  }

  async function download(): Promise<void> {
    const api = window.electron?.update
    if (!api) return
    status.value = await api.download()
  }

  function install(): void {
    window.electron?.update.install()
  }

  return { status, init, check, download, install }
})
