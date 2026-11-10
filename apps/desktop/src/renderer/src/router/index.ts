import { createRouter, createWebHashHistory } from 'vue-router'
import { routes } from './route'
import { logger } from '@/infrastructure/logging/logger'
import { isSectionHidden } from '@/domain/visibility'
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局路由守卫：隐藏分区直达时重定向首页，其余仅记录导航
router.beforeEach((to) => {
  if (isSectionHidden(to.path)) return { path: '/' }
  logger.info('[renderer] navigating to', to.fullPath)
})

export default router
