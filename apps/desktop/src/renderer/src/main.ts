import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { addCollection } from '@iconify/vue'
import mdi from '@iconify-json/mdi/icons.json'
import router from './router'
import App from './App.vue'
import './ui/styles/global.css'

// 本地注册 mdi，避免运行时请求 api.iconify.design（被 CSP 拦截）
addCollection(mdi)

createApp(App).use(createPinia()).use(router).mount('#app')
