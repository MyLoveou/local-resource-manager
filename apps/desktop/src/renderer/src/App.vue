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
  <div class="container">
    <ToolBar />
    <div class="app-container">
      <MenuBar :items="menuItems" />
      <main class="main-content">
        <router-view />
      </main>
      <InfoPanel />
    </div>
  </div>
</template>

<style scoped lang="less">
.container {
  display: flex;
  flex-direction: column;
  height: 100%;

  .app-container {
    display: flex;
    flex-direction: row;
    flex: 1;
    min-height: 0;
  }
}

.main-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
</style>
