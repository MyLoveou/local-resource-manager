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
]