<template>
  <div class="min-h-screen flex flex-col">
    <!-- 顶部导航 -->
    <nav class="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
      <div class="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-2 text-xl font-bold text-gold">
          <span class="text-2xl">☰</span>
          <span>天工</span>
        </router-link>

        <!-- 导航链接 -->
        <div class="hidden md:flex items-center gap-1">
          <router-link v-for="item in navItems" :key="item.path" :to="item.path"
            class="px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 transition-colors"
            active-class="text-amber-400 bg-amber-900/20">
            {{ item.label }}
          </router-link>
        </div>

        <!-- 右侧状态 -->
        <div class="flex items-center gap-3">
          <span class="flex items-center gap-1.5 text-xs text-gray-500">
            <span class="w-2 h-2 rounded-full" :class="store.isOnline ? 'bg-green-500' : 'bg-red-500'" />
            {{ store.isOnline ? '在线' : '离线' }}
          </span>
          <!-- 移动端菜单按钮 -->
          <button @click="menuOpen = !menuOpen" class="md:hidden btn-secondary !px-2 !py-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 移动端菜单 -->
      <div v-if="menuOpen" class="md:hidden border-t border-gray-800 bg-gray-950">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path"
          @click="menuOpen = false"
          class="block px-4 py-2.5 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
          active-class="text-amber-400 bg-amber-900/20">
          {{ item.label }}
        </router-link>
      </div>
    </nav>

    <!-- 主体 -->
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 底部 -->
    <footer class="border-t border-gray-800 py-4 text-center text-xs text-gray-600">
      天工 · 中华文明数字永生体 v2.13.0
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from './stores/app'

const store = useAppStore()
const menuOpen = ref(false)

const navItems = [
  { path: '/', label: '仪表盘' },
  { path: '/bazi', label: '八字' },
  { path: '/ziwei', label: '紫微' },
  { path: '/qimen', label: '奇门' },
  { path: '/liuyao', label: '六爻' },
  { path: '/fusion', label: '融合' },
  { path: '/cases', label: '案例库' },
  { path: '/admin', label: '管理' },
]

onMounted(() => {
  store.fetchHealth()
  setInterval(() => store.fetchHealth(), 30000)
})
</script>