import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./pages/Home.vue'),
  },
]

export default createRouter({
  history: createWebHistory('/apnaslot/'),
  routes,
})
