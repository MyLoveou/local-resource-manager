import { createRouter, createWebHashHistory } from 'vue-router'
import { routes } from './route'
import { logger } from '@/infrastructure/logging/logger'
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局路由守卫（Vue Router 5：勿用 next()，无返回值即放行）
router.beforeEach((to) => {
  logger.info('[renderer] navigating to', to.fullPath)
})

export default router
