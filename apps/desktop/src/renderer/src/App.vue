<script setup lang="ts">
import { computed } from 'vue'
import MenuBar from '@/ui/layouts/MenuBar/index.vue'
import ToolBar from '@/ui/layouts/ToolBar/index.vue'
import InfoPanel from '@/ui/layouts/InfoPanel/index.vue'
import { routes } from '@/router/route'
import { menuFromRoutes } from '@/domain/menu'

const menuItems = computed(() => menuFromRoutes(routes))
</script>

<template>
  <!-- 顶部工具栏 -->
  <ToolBar />
  <!-- 左侧导航栏 -->
  <div class="app-container">
    <MenuBar :items="menuItems" />

    <!-- 主内容区域 -->
    <main class="main-content">
      <router-view />
    </main>
    <!-- 右侧信息面板 -->
    <InfoPanel />
  </div>
</template>

<style scoped lang="less">
.app-container {
  display: flex;
  flex-direction: row;
  height: 100%;
}

.main-content {
  flex: 1;
  overflow: auto;
}
</style>
