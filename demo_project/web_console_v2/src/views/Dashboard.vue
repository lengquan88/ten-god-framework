<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">系统仪表盘</h1>

    <!-- 状态卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="card card-hover">
        <div class="text-sm text-gray-500 mb-1">系统状态</div>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full" :class="store.isOnline ? 'bg-green-500' : 'bg-red-500'" />
          <span class="text-xl font-bold">{{ store.isOnline ? '健康' : '离线' }}</span>
        </div>
      </div>
      <div class="card card-hover">
        <div class="text-sm text-gray-500 mb-1">案例总数</div>
        <div class="text-xl font-bold text-amber-400">{{ store.dbStats?.cases || 0 }}</div>
      </div>
      <div class="card card-hover">
        <div class="text-sm text-gray-500 mb-1">反馈总数</div>
        <div class="text-xl font-bold text-blue-400">{{ store.dbStats?.feedback || 0 }}</div>
      </div>
      <div class="card card-hover">
        <div class="text-sm text-gray-500 mb-1">知识图谱</div>
        <div class="text-xl font-bold text-purple-400">{{ (store.dbStats?.kg_nodes || 0) + (store.dbStats?.kg_edges || 0) }}</div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="mb-8">
      <h2 class="text-lg font-semibold mb-4">快捷入口</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <router-link v-for="item in quickLinks" :key="item.path" :to="item.path"
          class="card card-hover flex flex-col items-center justify-center py-8 gap-2">
          <span class="text-3xl">{{ item.icon }}</span>
          <span class="text-sm text-gray-400">{{ item.label }}</span>
          <span class="text-xs text-gray-600">{{ item.desc }}</span>
        </router-link>
      </div>
    </div>

    <!-- 统计与数据库 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="card">
        <h3 class="text-lg font-semibold mb-4">数据库统计</h3>
        <div v-if="store.dbStats" class="space-y-2">
          <div v-for="(v, k) in store.dbStats" :key="k" class="flex justify-between py-1 border-b border-gray-800 last:border-0">
            <span class="text-gray-400">{{ k }}</span>
            <span class="text-gray-200 font-mono">{{ v }}</span>
          </div>
        </div>
        <div v-else class="text-gray-500 text-sm">暂无数据</div>
      </div>

      <div class="card">
        <h3 class="text-lg font-semibold mb-4">快速操作</h3>
        <div class="flex flex-wrap gap-2">
          <button @click="refresh" class="btn-secondary" :disabled="loading">
            {{ loading ? '刷新中...' : '刷新数据' }}
          </button>
          <router-link to="/bazi" class="btn-primary">八字排盘</router-link>
          <router-link to="/cases" class="btn-secondary">案例管理</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const loading = ref(false)

const quickLinks = [
  { path: '/bazi', icon: '🔮', label: '八字排盘', desc: '四柱八字命理分析' },
  { path: '/ziwei', icon: '⭐', label: '紫微斗数', desc: '十二宫星曜推演' },
  { path: '/qimen', icon: '🧭', label: '奇门遁甲', desc: '时空九宫推演' },
  { path: '/liuyao', icon: '🪙', label: '六爻占卜', desc: '铜钱起卦断卦' },
  { path: '/fusion', icon: '🔄', label: '融合分析', desc: '多体系交叉验证' },
  { path: '/cases', icon: '📚', label: '案例库', desc: '历史案例检索' },
  { path: '/admin', icon: '⚙️', label: '管理面板', desc: '系统管理后台' },
  { path: '/settings', icon: '🔧', label: '系统设置', desc: '配置与偏好' },
]

async function refresh() {
  loading.value = true
  await Promise.all([store.fetchHealth(), store.fetchDbStats()])
  loading.value = false
}

onMounted(() => { store.fetchDbStats() })
</script>