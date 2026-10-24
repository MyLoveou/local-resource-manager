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
    path: '/characters',
    name: 'Characters',
    component: () => import('@/views/Characters/index.vue'),
    meta: {
      title: '角色',
      icon: 'account-group',
    },
  },
  {
    path: '/characters/:id',
    name: 'CharacterDetail',
    component: () => import('@/views/CharacterDetail/index.vue'),
    meta: {
      title: '角色',
      hideMenu: true,
    },
  },
  {
    path: '/persons',
    name: 'Persons',
    component: () => import('@/views/Persons/index.vue'),
    meta: {
      title: '扮演者',
      icon: 'account-star',
    },
  },
  {
    path: '/persons/:id',
    name: 'PersonDetail',
    component: () => import('@/views/PersonDetail/index.vue'),
    meta: {
      title: '扮演者',
      hideMenu: true,
    },
  },
  {
    path: '/ai',
    name: 'AI',
    component: () => import('@/views/AI/index.vue'),
    meta: {
      title: 'AI 中心',
      icon: 'robot',
      menuGroup: 'tools',
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
    path: '/maps',
    name: 'Maps',
    component: () => import('@/views/Maps/index.vue'),
    meta: {
      title: '地图',
      icon: 'map',
    },
  },
  {
    path: '/maps/:id',
    name: 'MapDetail',
    component: () => import('@/views/MapDetail/index.vue'),
    meta: {
      title: '地图',
      hideMenu: true,
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
