import type { RouteRecordRaw } from 'vue-router'
import { TYPE_PROFILES } from '@/domain/libraryTypes'

const typeBrowse = () => import('@/views/TypeBrowse/index.vue')

const typeRoutes: RouteRecordRaw[] = TYPE_PROFILES.map((profile) => ({
  path: profile.routePath,
  name: profile.type,
  component: typeBrowse,
  meta: {
    title: profile.label,
    icon: profile.routeIcon,
    resourceType: profile.type,
  },
}))

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home/index.vue'),
    meta: {
      title: '首页',
      icon: 'home',
    },
  },
  ...typeRoutes,
  {
    path: '/trash',
    name: 'Trash',
    component: () => import('@/views/Trash/index.vue'),
    meta: {
      title: '回收站',
      icon: 'delete',
    },
  },
]
