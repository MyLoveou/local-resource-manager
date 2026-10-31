/** 浏览视图选项（跨分区共享，持久化） */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useViewOptionsStore = defineStore(
  'viewOptions',
  () => {
    /** 主库列表是否显示已加入合集的资源 */
    const includeCollected = ref(false)

    function setIncludeCollected(value: boolean): void {
      includeCollected.value = value
    }

    return { includeCollected, setIncludeCollected }
  },
  { persist: { pick: ['includeCollected'] } }
)
