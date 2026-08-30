<script setup lang="ts">
import { ref } from 'vue'

const version = ref(`Electron ${window.electron?.versions.electron ?? '?'} · Chrome ${window.electron?.versions.chrome ?? '?'}`)
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <h1>本地资源管理器</h1>
      <span class="version">{{ version }}</span>
    </header>
    <main class="placeholder">
      <p>项目骨架已就绪，业务功能按需求逐步实现。</p>
      <p class="hint">分层目录：ui / application / domain / infrastructure</p>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: system-ui, 'Microsoft YaHei', sans-serif;
}
.topbar {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #e5e7eb;
}
.topbar h1 {
  font-size: 16px;
  font-weight: 600;
}
.version {
  font-size: 12px;
  color: #6b7280;
}
.placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #374151;
}
.hint {
  font-size: 13px;
  color: #9ca3af;
}
</style>
