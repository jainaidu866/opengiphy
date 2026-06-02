import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { useAuth } from '@/stores/auth'
import HomeView from '@/views/HomeView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/create',
    name: 'create',
    component: () => import('@/views/CreateView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('@/views/UploadView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/categories',
    name: 'categories',
    component: () => import('@/views/CategoriesView.vue'),
  },
  {
    path: '/category/:name',
    name: 'category',
    component: () => import('@/views/CategoryView.vue'),
  },
  {
    path: '/collections',
    name: 'collections',
    component: () => import('@/views/CollectionsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/gif/:id',
    name: 'gif-detail',
    component: () => import('@/views/GifDetailView.vue'),
  },
  {
    path: '/profile/:username',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const { isLoggedIn } = useAuth()

  // Protected routes (e.g. /upload) require a logged-in user.
  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Logged-in users shouldn't see the login/register pages.
  if (to.meta.guestOnly && isLoggedIn.value) {
    return { name: 'home' }
  }

  return true
})

export default router
