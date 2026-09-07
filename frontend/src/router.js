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
    path: '/venues/:slug',
    name: 'Venue',
    component: () => import('./pages/VenuePage.vue'),
  },
  {
    path: '/checkout/:booking',
    name: 'Checkout',
    component: () => import('./pages/Checkout.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/pay/:token',
    name: 'Pay',
    component: () => import('./pages/Pay.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/manage/onboarding',
    name: 'Onboarding',
    component: () => import('./pages/manage/Onboarding.vue'),
    meta: { requiresAuth: true, requiresNoPublisher: true },
  },
  {
    path: '/manage/venues',
    name: 'Venues',
    component: () => import('./pages/manage/Venues.vue'),
    meta: { requiresAuth: true, requiresPublisher: true },
  },
  {
    path: '/manage/venues/new',
    name: 'NewVenue',
    component: () => import('./pages/manage/NewVenue.vue'),
    meta: { requiresAuth: true, requiresPublisher: true },
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
  if (to.meta.requiresPublisher && !session.publishers.length) return { name: 'Onboarding' }
})

export default router
