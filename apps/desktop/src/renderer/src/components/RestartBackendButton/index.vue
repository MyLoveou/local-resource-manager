<template>
  <div class="restart-backend">
    <n-button size="small" :loading="restarting" @click="run">重启后端服务</n-button>
    <span class="restart-backend__hint">改完后端代码后不用退出应用，这里直接重启服务</span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton } from 'naive-ui'
import { notify } from '@/application/notify'

const restarting = ref(false)

async function run(): Promise<void> {
  restarting.value = true
  try {
    const result = await window.electron.restartBackend()
    notify.toast.success(result.changed ? '后端已重启（地址变化，窗口已重开）' : '后端已重启')
  } catch {
    notify.toast.error('重启后端失败')
  } finally {
    restarting.value = false
  }
}
</script>

<style scoped lang="less">
.restart-backend {
  display: flex;
  align-items: center;
  gap: 10px;
}

.restart-backend__hint {
  font-size: 12px;
  color: var(--sm-color-text-muted, #6b7280);
}
</style>
