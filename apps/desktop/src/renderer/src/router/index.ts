import { createRouter, createWebHashHistory } from 'vue-router'
import { routes } from './route'
import { logger } from '@/infrastructure/logging/logger'
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  logger.info('[renderer] navigating to', to.fullPath)
  next()
})

export default router
