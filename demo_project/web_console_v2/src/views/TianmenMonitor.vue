<template>
  <div class="p-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gold">天眼监控</h1>
        <p class="text-sm text-gray-500 mt-1">天门开阖 · 知止不殆 · 混沌海探索</p>
      </div>
      <span class="text-xs text-gray-600" :class="live ? 'text-green-500' : 'text-red-500'">
        <span class="w-2 h-2 rounded-full inline-block mr-1" :class="live ? 'bg-green-500' : 'bg-red-500'" />
        {{ live ? '天眼运行中' : '天眼离线' }}
      </span>
    </div>

    <!-- 标签页 -->
    <div class="flex gap-1 mb-4 border-b border-gray-800">
      <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
        class="px-4 py-2 text-sm rounded-t-lg transition-colors"
        :class="activeTab === tab.id ? 'bg-gray-900 text-amber-400 border border-b-0 border-gray-800' : 'text-gray-500 hover:text-gray-300'">
        {{ tab.label }}
      </button>
    </div>

    <!-- 门禁统计 -->
    <div v-if="activeTab === 'gate'" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="总请求" :value="stats.total_requests" color="blue" />
        <StatCard label="拦截数" :value="stats.blocked_requests" color="red" />
        <StatCard label="自修正" :value="stats.corrected_requests" color="green" />
        <StatCard label="拦截率" :value="(stats.block_rate * 100).toFixed(1) + '%'" color="amber" />
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="天眼门禁" :value="stats.tianmen?.total || 0" color="purple" />
        <StatCard label="通过率" :value="(stats.tianmen?.pass_rate * 100 || 0).toFixed(1) + '%'" color="green" />
        <StatCard label="回退率" :value="(stats.tianmen?.retreat_rate * 100 || 0).toFixed(1) + '%'" color="red" />
        <StatCard label="元气" :value="(stats.tianmen?.avg_qi || 0).toFixed(3)" color="amber" />
      </div>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatCard label="修正成功率" :value="(stats.correction?.success_rate * 100 || 0).toFixed(1) + '%'" color="green" />
        <StatCard label="修正总数" :value="stats.correction?.total_corrections || 0" color="blue" />
        <StatCard label="自适应阈值" :value="(stats.tianmen?.adaptive_threshold || 0).toFixed(3)" color="purple" />
      </div>
    </div>

    <!-- 修真九境 -->
    <div v-if="activeTab === 'xiuzhen'" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="当前境界" :value="xiuzhen.current_realm?.name || '—'" color="amber" />
        <StatCard label="累积元气" :value="(xiuzhen.total_qi || 0).toFixed(3)" color="blue" />
        <StatCard label="修行天数" :value="xiuzhen.cultivation_days || 0" color="purple" />
        <StatCard label="突破次数" :value="xiuzhen.breakthroughs || 0" color="green" />
      </div>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatCard label="心魔劫通过" :value="xiuzhen.heart_demon_passed || 0" color="green" />
        <StatCard label="心魔劫尝试" :value="xiuzhen.heart_demon_attempts || 0" color="red" />
        <StatCard label="通过率" :value="((xiuzhen.heart_demon_passed / Math.max(1, xiuzhen.heart_demon_attempts)) * 100).toFixed(1) + '%'" color="amber" />
      </div>
      <!-- 九境进度条 -->
      <div class="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h3 class="text-sm font-semibold text-gray-300 mb-3">修真九境</h3>
        <div class="space-y-2">
          <div v-for="realm in xiuzhen.all_realms || []" :key="realm.index" class="flex items-center gap-3">
            <span class="w-16 text-xs text-gray-500 text-right">{{ realm.name }}</span>
            <div class="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all duration-700"
                :class="realm.passed ? 'bg-green-500' : realm.current ? 'bg-amber-500 animate-pulse' : 'bg-gray-700'"
                :style="{ width: realm.passed ? '100%' : realm.current ? xiuzhenProgressPercent + '%' : '0%' }" />
            </div>
            <span class="w-12 text-xs text-gray-600 text-left">{{ realm.threshold }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 混沌海 -->
    <div v-if="activeTab === 'hundun'" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="浮沫总数" :value="hundun.total || 0" color="purple" />
        <StatCard label="未验证" :value="hundun.floating || 0" color="amber" />
        <StatCard label="已验证" :value="hundun.verified || 0" color="green" />
        <StatCard label="探索次数" :value="hundun.exploration_count || 0" color="blue" />
      </div>
      <div class="bg-gray-900 rounded-lg p-4 border border-gray-800 max-h-96 overflow-y-auto">
        <h3 class="text-sm font-semibold text-gray-300 mb-3">浮沫坐标</h3>
        <div v-if="(hundun.foams || []).length === 0" class="text-center text-gray-600 py-8">
          混沌海中尚无浮沫，等待探索触发...
        </div>
        <div v-else class="space-y-2">
          <div v-for="foam in hundun.foams" :key="foam.feature_a + foam.feature_b"
            class="flex items-center justify-between p-2 rounded bg-gray-800/50">
            <div class="flex items-center gap-2">
              <span class="text-xs text-amber-400">{{ foam.feature_a }}</span>
              <span class="text-xs text-gray-600">↔</span>
              <span class="text-xs text-amber-400">{{ foam.feature_b }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs text-gray-500">{{ (foam.correlation_strength * 100).toFixed(1) }}%</span>
              <span class="text-xs px-2 py-0.5 rounded"
                :class="foam.status === 'verified' ? 'bg-green-900/50 text-green-400' : 'bg-amber-900/50 text-amber-400'">
                {{ foam.status === 'verified' ? '已验证' : '浮沫' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 自修正日志 -->
    <div v-if="activeTab === 'correction'" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatCard label="修正总数" :value="correction.total_corrections || 0" color="blue" />
        <StatCard label="成功次数" :value="correction.successful || 0" color="green" />
        <StatCard label="成功率" :value="((correction.success_rate || 0) * 100).toFixed(1) + '%'" color="amber" />
      </div>
      <div class="bg-gray-900 rounded-lg p-4 border border-gray-800 max-h-96 overflow-y-auto">
        <h3 class="text-sm font-semibold text-gray-300 mb-3">修正记录</h3>
        <div v-if="(correction.recent_reports || []).length === 0" class="text-center text-gray-600 py-8">
          暂无自修正记录
        </div>
        <div v-else class="space-y-3">
          <div v-for="report in correction.recent_reports" :key="report.session_id"
            class="p-3 rounded bg-gray-800/50 border border-gray-700/50">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-gray-400">{{ report.session_id }}</span>
              <span class="text-xs px-2 py-0.5 rounded"
                :class="report.success ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'">
                {{ report.success ? '成功' : '失败' }}
              </span>
            </div>
            <div class="flex gap-1 flex-wrap">
              <span v-for="step in report.steps" :key="step.step"
                class="text-xs px-2 py-0.5 rounded bg-gray-700/50"
                :class="step.status === 'completed' ? 'text-green-400' : 'text-gray-500'"
                :title="`${step.name}(${step.tech}) Δ=${step.delta}`">
                {{ step.step }}.{{ step.name }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 回头看 -->
    <div v-if="activeTab === 'huigu'" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="总步数" :value="huigu.total_steps || 0" color="blue" />
        <StatCard label="静默次数" :value="huigu.silent_count || 0" color="amber" />
        <StatCard label="回忆次数" :value="huigu.recall_count || 0" color="purple" />
        <StatCard label="轨迹健康度" :value="((huigu.trajectory_health || 0) * 100).toFixed(1) + '%'" color="green" />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <StatCard label="静默率" :value="((huigu.silent_rate || 0) * 100).toFixed(1) + '%'" color="amber" />
        <StatCard label="回忆率" :value="((huigu.recall_rate || 0) * 100).toFixed(1) + '%'" color="purple" />
      </div>
      <div class="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h3 class="text-sm font-semibold text-gray-300 mb-3">调度参数</h3>
        <div class="grid grid-cols-2 gap-3">
          <StatCard label="回溯窗口" :value="huigu.window_size || 0" color="blue" />
          <StatCard label="最大偏离角" :value="(huigu.max_angle || 0) + '°'" color="amber" />
        </div>
      </div>
    </div>

    <!-- 刷新按钮 -->
    <div class="flex justify-center mt-6">
      <button @click="fetchAll" class="btn-secondary text-sm" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getGateStats, getXiuzhenProgress, getHundunFoams, getCorrectionLog, getHuiguStatus } from '../api'

const activeTab = ref('gate')
const loading = ref(false)
const live = ref(false)

const stats = ref({ total_requests: 0, blocked_requests: 0, corrected_requests: 0, block_rate: 0, correction_rate: 0, tianmen: {}, correction: {} })
const xiuzhen = ref({ current_realm: {}, all_realms: [], total_qi: 0, cultivation_days: 0, breakthroughs: 0, heart_demon_attempts: 0, heart_demon_passed: 0 })
const hundun = ref({ foams: [], total: 0, floating: 0, verified: 0, exploration_count: 0, discovery_count: 0 })
const correction = ref({ total_corrections: 0, successful: 0, success_rate: 0, recent_reports: [] })
const huigu = ref({ total_steps: 0, silent_count: 0, recall_count: 0, silent_rate: 0, recall_rate: 0, trajectory_health: 0, window_size: 0, max_angle: 0 })

const tabs = [
  { id: 'gate', label: '门禁统计' },
  { id: 'xiuzhen', label: '修真九境' },
  { id: 'hundun', label: '混沌海' },
  { id: 'correction', label: '自修正' },
  { id: 'huigu', label: '回头看' },
]

const xiuzhenProgressPercent = computed(() => {
  const realm = xiuzhen.value.all_realms?.find(r => r.current)
  if (!realm || !xiuzhen.value.next_realm) return 0
  const needed = (xiuzhen.value.next_realm?.required_qi || 0.01)
  return Math.min(100, (xiuzhen.value.total_qi / needed) * 100)
})

async function fetchAll() {
  loading.value = true
  try {
    const [s, x, h, c, hu] = await Promise.allSettled([
      getGateStats(),
      getXiuzhenProgress(),
      getHundunFoams(),
      getCorrectionLog(),
      getHuiguStatus(),
    ])
    if (s.status === 'fulfilled') stats.value = s.value.data || s.value
    if (x.status === 'fulfilled') xiuzhen.value = x.value.data || x.value
    if (h.status === 'fulfilled') hundun.value = h.value.data || h.value
    if (c.status === 'fulfilled') correction.value = c.value.data || c.value
    if (hu.status === 'fulfilled') huigu.value = hu.value.data || hu.value
    live.value = true
  } catch (e) {
    live.value = false
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAll()
  setInterval(fetchAll, 10000)
})
</script>

<style scoped>
.btn-secondary {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  background: rgba(55, 65, 81, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.5);
  color: #9ca3af;
  transition: all 0.2s;
}
.btn-secondary:hover:not(:disabled) {
  background: rgba(75, 85, 99, 0.5);
  color: #d1d5db;
}
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.text-gold { color: #f59e0b; }
</style>