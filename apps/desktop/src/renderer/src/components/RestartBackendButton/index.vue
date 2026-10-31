<template>
  <div class="restart-backend">
    <n-button size="small" :loading="restarting" @click="run">重启后端</n-button>
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

</style>
