import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/bazi', name: 'Bazi', component: () => import('../views/BaziView.vue') },
  { path: '/ziwei', name: 'Ziwei', component: () => import('../views/ZiweiView.vue') },
  { path: '/qimen', name: 'Qimen', component: () => import('../views/QimenView.vue') },
  { path: '/liuyao', name: 'Liuyao', component: () => import('../views/LiuyaoView.vue') },
  { path: '/fusion', name: 'Fusion', component: () => import('../views/FusionView.vue') },
  { path: '/cases', name: 'Cases', component: () => import('../views/CaseLibrary.vue') },
  { path: '/admin', name: 'Admin', component: () => import('../views/AdminPanel.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router