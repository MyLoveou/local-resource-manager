<script setup lang="ts">
import { computed } from 'vue'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import MenuBar from '@/ui/layouts/MenuBar/index.vue'
import ToolBar from '@/ui/layouts/ToolBar/index.vue'
import UpdateBanner from '@/components/UpdateBanner/index.vue'
import InfoPanel from '@/ui/layouts/InfoPanel/index.vue'
import AppShell from '@/ui/layouts/AppShell/index.vue'
import ImageViewerOverlay from '@/components/ImageViewerOverlay/index.vue'
import VideoPlayerOverlay from '@/components/VideoPlayerOverlay/index.vue'
import AudioPlayerOverlay from '@/components/AudioPlayerOverlay/index.vue'
import ModelPreviewOverlay from '@/components/ModelPreviewOverlay/index.vue'
import { routes } from '@/router/route'
import { menuFromRoutes } from '@/domain/menu'
import { isSectionHidden } from '@/domain/visibility'
import { useThemeStore } from '@/application/stores/theme'
import { readNaiveOverrides } from '@/ui/theme/applyTheme'
import { useWatchAutoRefresh } from '@/hooks/useWatchAutoRefresh'

const menuItems = computed(() => menuFromRoutes(routes, isSectionHidden))
const theme = useThemeStore()
const themeOverrides = computed(() => {
  void theme.revision
  return readNaiveOverrides()
})
// 监视目录自动导入后，轮询检测并刷新资源列表
useWatchAutoRefresh()
</script>

<template>
  <n-config-provider
    abstract
    :theme-overrides="themeOverrides"
  >
    <n-message-provider>
      <AppShell>
        <template #top>
          <ToolBar />
        </template>
        <template #banner>
          <UpdateBanner />
        </template>
        <template #sidebar>
          <MenuBar :items="menuItems" />
        </template>
        <router-view />
        <ImageViewerOverlay />
        <VideoPlayerOverlay />
        <AudioPlayerOverlay />
        <ModelPreviewOverlay />
        <template #inspector>
          <InfoPanel />
        </template>
      </AppShell>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped lang="less">
</style>
