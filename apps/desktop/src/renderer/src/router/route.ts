import type { RouteRecordRaw } from 'vue-router'
import { TYPE_PROFILES } from '@/domain/libraryTypes'

const libraryWorkspace = () => import('@/views/LibraryWorkspace/index.vue')

const legacyTypeRoutes: RouteRecordRaw[] = TYPE_PROFILES.map((profile) => ({
  path: profile.routePath,
  redirect: `/library/${profile.type}`,
  meta: { hideMenu: true },
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
  {
    path: '/library',
    redirect: '/library/image',
    meta: {
      title: '资源库',
      icon: 'folder-multiple',
    },
  },
  {
    path: '/library/:type',
    name: 'Library',
    component: libraryWorkspace,
    meta: {
      title: '资源库',
      hideMenu: true,
    },
  },
  {
    path: '/library/:type/day/:date',
    name: 'PhotoDay',
    component: () => import('@/views/PhotoDay/index.vue'),
    meta: {
      title: '时间线',
      hideMenu: true,
    },
  },
  {
    path: '/timelines',
    name: 'Timelines',
    component: () => import('@/views/Timelines/index.vue'),
    meta: {
      title: '时间线',
      icon: 'chart-timeline-variant',
    },
  },
  {
    path: '/timelines/:id',
    name: 'TimelineDetail',
    component: () => import('@/views/TimelineDetail/index.vue'),
    meta: {
      title: '时间线',
      hideMenu: true,
    },
  },
  {
    path: '/photos',
    redirect: '/timelines/all',
    meta: { hideMenu: true },
  },
  {
    path: '/photos/day/:date',
    redirect: (to) => `/library/image/day/${String(to.params.date ?? '')}`,
    meta: { hideMenu: true },
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
  ...legacyTypeRoutes,
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
