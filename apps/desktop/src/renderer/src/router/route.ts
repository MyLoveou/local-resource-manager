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

const photoRoutes: RouteRecordRaw[] = [
  {
    path: '/photos',
    name: 'Photos',
    component: () => import('@/views/Photos/index.vue'),
    meta: {
      title: '时间线',
      icon: 'image-multiple',
    },
  },
  {
    path: '/photos/day/:date',
    name: 'PhotoDay',
    component: () => import('@/views/PhotoDay/index.vue'),
    meta: {
      title: '时间线',
      hideMenu: true,
    },
  },
]

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
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/Search/index.vue'),
    meta: {
      title: '搜索',
      hideMenu: true,
    },
  },
  ...typeRoutes.slice(0, 1),
  ...photoRoutes,
  ...typeRoutes.slice(1),
  {
    path: '/collections',
    name: 'Collections',
    component: () => import('@/views/Collections/index.vue'),
    meta: {
      title: '合集',
      icon: 'folder-multiple',
    },
  },
  {
    path: '/collections/:id',
    name: 'CollectionDetail',
    component: () => import('@/views/CollectionDetail/index.vue'),
    meta: {
      title: '合集',
      hideMenu: true,
    },
  },
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
