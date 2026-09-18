import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { addCollection } from '@iconify/vue'
import mdi from '@iconify-json/mdi/icons.json'
import router from './router'
import App from './App.vue'
import './ui/styles/tokens.css'
import './ui/themes/default.css'
import './ui/themes/dark.css'
import './ui/styles/global.css'
import 'video.js/dist/video-js.css'
import VueVideoPlayer from 'vue-video-player'
import { useThemeStore } from './application/stores/theme'

// 本地注册 mdi，避免运行时请求 api.iconify.design（被 CSP 拦截）
addCollection(mdi)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

const app = createApp(App)
app.use(pinia)

async function boot(): Promise<void> {
  try {
    await useThemeStore().hydrate()
  } catch (err) {
    console.error(err)
  }
  app.use(router).use(VueVideoPlayer).mount('#app')
}

void boot()
