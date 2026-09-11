<template>
  <header class="tool-bar">
    <n-button size="small" type="primary" @click="wizardRef?.open()">导入</n-button>
    <ImportWizard ref="wizardRef" />
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton } from 'naive-ui'
import ImportWizard from '@/components/ImportWizard/index.vue'

const wizardRef = ref<{ open: () => void } | null>(null)
</script>

<style scoped lang="less">
.tool-bar {
  height: 40px;
  background-color: #fff;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 8px;
}
</style>
