/**
 * 监视导入自动刷新：轮询 watch-revision，修订号变化时软刷新对应类型列表。
 * 挂载在 App 壳（全局生效）。
 */
import { onMounted, onUnmounted } from 'vue'
import { getWatchRevision } from '@/infrastructure/http/resources'
import { invalidateTags } from '@/infrastructure/http/vocab'
import { useLibraryStore } from '@/application/stores/library'
import type { ResourceType } from '@/domain'

const POLL_INTERVAL_MS = 3000

export function useWatchAutoRefresh(): void {
  const library = useLibraryStore()
  let timer: number | undefined
  let lastRevision: number | null = null

  async function poll(): Promise<void> {
    try {
      const snapshot = await getWatchRevision()
      if (lastRevision !== null && snapshot.revision !== lastRevision && snapshot.type) {
        invalidateTags()
        library.watchBump(snapshot.type as ResourceType)
      }
      lastRevision = snapshot.revision
    } catch {
      // 后端未起/瞬断：静默，等下次轮询
    }
  }

  onMounted(() => {
    void poll()
    timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS)
  })

  onUnmounted(() => {
    if (timer !== undefined) window.clearInterval(timer)
  })
}
