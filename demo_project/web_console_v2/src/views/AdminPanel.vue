<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">管理面板</h1>

    <!-- 数据库统计 -->
    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">数据库统计</h2>
      <div v-if="dbStats" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div v-for="(v, k) in dbStats" :key="k" class="bg-gray-800 rounded-lg p-3 text-center">
          <div class="text-xs text-gray-500">{{ k }}</div>
          <div class="text-xl font-bold text-amber-400 mt-1">{{ v }}</div>
        </div>
      </div>
      <div v-else class="text-gray-500 text-sm">加载中...</div>
    </div>

    <!-- 反馈统计 -->
    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">反馈统计</h2>
      <div v-if="feedbackStats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-gray-800 rounded-lg p-3 text-center">
          <div class="text-xs text-gray-500">总反馈</div>
          <div class="text-xl font-bold text-amber-400">{{ feedbackStats.total }}</div>
        </div>
        <div class="bg-gray-800 rounded-lg p-3 text-center">
          <div class="text-xs text-gray-500">平均准确度</div>
          <div class="text-xl font-bold text-green-400">{{ feedbackStats.avg_accuracy }}</div>
        </div>
        <div class="bg-gray-800 rounded-lg p-3 text-center">
          <div class="text-xs text-gray-500">平均满意度</div>
          <div class="text-xl font-bold text-blue-400">{{ feedbackStats.avg_satisfaction }}</div>
        </div>
        <div class="bg-gray-800 rounded-lg p-3 text-center">
          <div class="text-xs text-gray-500">平均有用性</div>
          <div class="text-xl font-bold text-purple-400">{{ feedbackStats.avg_usefulness }}</div>
        </div>
      </div>
    </div>

    <!-- 操作区 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">数据备份</h2>
        <p class="text-sm text-gray-400 mb-3">导出全量数据库备份</p>
        <button @click="doBackup" class="btn-primary" :disabled="backingUp">
          {{ backingUp ? '备份中...' : '全量备份' }}
        </button>
      </div>

      <div class="card">
        <h2 class="text-lg font-semibold mb-4">数据恢复</h2>
        <p class="text-sm text-gray-400 mb-3">从备份文件恢复数据</p>
        <textarea v-model="restoreJson" class="input-field h-24 mb-2" placeholder="粘贴备份数据..."></textarea>
        <button @click="doRestore" class="btn-danger" :disabled="!restoreJson || restoring">
          {{ restoring ? '恢复中...' : '恢复数据' }}
        </button>
      </div>
    </div>

    <p v-if="msg" class="mt-4 text-sm" :class="msgError ? 'text-red-400' : 'text-green-400'">{{ msg }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDbStats, getFeedbackStats, backupDb, restoreDb } from '../api'

const dbStats = ref(null)
const feedbackStats = ref(null)
const backingUp = ref(false)
const restoring = ref(false)
const restoreJson = ref('')
const msg = ref('')
const msgError = ref(false)

async function fetchStats() {
  try {
    const [db, fb] = await Promise.all([getDbStats(), getFeedbackStats()])
    dbStats.value = db.data
    feedbackStats.value = fb.data
  } catch { /* ignore */ }
}

async function doBackup() {
  backingUp.value = true
  try {
    const { data } = await backupDb()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `backup_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    msg.value = '备份成功'
    msgError.value = false
  } catch (e) {
    msg.value = '备份失败：' + e.message
    msgError.value = true
  } finally {
    backingUp.value = false
  }
}

async function doRestore() {
  if (!confirm('确认恢复数据？这将覆盖当前数据！')) return
  restoring.value = true
  try {
    const parsed = JSON.parse(restoreJson.value)
    await restoreDb(parsed)
    msg.value = '恢复成功'
    msgError.value = false
    restoreJson.value = ''
    fetchStats()
  } catch (e) {
    msg.value = '恢复失败：' + e.message
    msgError.value = true
  } finally {
    restoring.value = false
  }
}

onMounted(fetchStats)
</script>