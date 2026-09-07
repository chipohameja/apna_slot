import { createRouter, createWebHistory } from 'vue-router'

import { loadSession, session } from './session'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./pages/Home.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('./pages/Login.vue'),
    meta: { requiresGuest: true },
  },
  {
    path: '/signup',
    name: 'SignUp',
    component: () => import('./pages/SignUp.vue'),
    meta: { requiresGuest: true },
  },
  {
    path: '/manage/onboarding',
    name: 'Onboarding',
    component: () => import('./pages/manage/Onboarding.vue'),
    meta: { requiresAuth: true, requiresNoPublisher: true },
  },
]

const router = createRouter({
  history: createWebHistory('/apnaslot/'),
  routes,
})

router.beforeEach(async (to) => {
  if (!session.isReady) await loadSession()
  if (to.meta.requiresGuest && !session.is_guest) return { name: 'Home' }
  if (to.meta.requiresAuth && session.is_guest) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresNoPublisher && session.publishers.length) return { name: 'Home' }
})

export default router
