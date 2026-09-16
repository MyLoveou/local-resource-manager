import type { RouteRecordRaw } from 'vue-router'
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home/index.vue'),
    meta: {
      title: '首页',
      icon: 'home',
    }
  },
  {
    path: '/image',
    name: 'Image',
    component: () => import('@/views/Image/index.vue'),
    meta: {
      title: '图片',
      icon: 'image',
    }
  },
  {
    path: '/video',
    name: 'Video',
    component: () => import('@/views/Video/index.vue'),
    meta: {
      title: '视频',
      icon: 'video',
    }
  },
  {
    path: '/anime',
    name: 'Anime',
    component: () => import('@/views/Anime/index.vue'),
    meta: {
      title: '番剧',
      icon: 'anime',
    }
  }, {
    path: '/av',
    name: 'AV',
    component: () => import('@/views/AV/index.vue'),
    meta: {
      title: 'AV',
      icon: 'av',
    }
  },
  {
    path: '/trash',
    name: 'Trash',
    component: () => import('@/views/Trash/index.vue'),
    meta: {
      title: '回收站',
      icon: 'delete',
    }
  },
]