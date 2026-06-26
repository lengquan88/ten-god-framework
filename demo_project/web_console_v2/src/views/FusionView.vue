<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">融合分析</h1>

    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">多体系综合分析</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">性别</label>
          <select v-model="form.gender" class="input-field">
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">出生日期</label>
          <input v-model="form.date" type="date" class="input-field" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">出生时间</label>
          <input v-model="form.time" type="time" class="input-field" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">分析年份</label>
          <input v-model="form.year" type="number" class="input-field" :min="1900" :max="2100" />
        </div>
      </div>
      <div class="flex gap-3 mt-4">
        <button @click="analyze" class="btn-primary" :disabled="loading">
          {{ loading ? '分析中...' : '开始分析' }}
        </button>
        <button @click="clear" class="btn-secondary">清空</button>
      </div>
      <p v-if="error" class="mt-3 text-red-400 text-sm">{{ error }}</p>
    </div>

    <div v-if="result" class="space-y-6">
      <!-- 一致性评分 -->
      <div class="card text-center">
        <h2 class="text-lg font-semibold mb-4">体系一致性</h2>
        <div class="text-4xl font-bold text-amber-400">{{ result.cross_validation?.score || '--' }}</div>
        <div class="text-sm text-gray-400 mt-1">{{ result.cross_validation?.level || '待观察' }}</div>
        <div v-if="result.cross_validation?.agreements?.length" class="mt-3 flex flex-wrap justify-center gap-2">
          <span v-for="a in result.cross_validation.agreements" :key="a" class="tag tag-active">{{ a }}</span>
        </div>
      </div>

      <!-- 各体系摘要 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="(sys, name) in result.systems" :key="name" class="card">
          <h3 class="text-sm font-semibold text-amber-400 mb-2">{{ name }}</h3>
          <p v-if="sys.summary" class="text-sm text-gray-300">{{ sys.summary }}</p>
          <p v-else class="text-sm text-gray-600">暂无数据</p>
        </div>
      </div>

      <!-- 共识运势 -->
      <div v-if="result.consensus" class="card">
        <h2 class="text-lg font-semibold mb-4">共识运势</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div class="bg-gray-800 rounded-lg p-3">
            <div class="text-xs text-gray-500">事业</div>
            <div class="text-lg font-bold text-amber-400">{{ result.consensus.career || '--' }}</div>
          </div>
          <div class="bg-gray-800 rounded-lg p-3">
            <div class="text-xs text-gray-500">财运</div>
            <div class="text-lg font-bold text-amber-400">{{ result.consensus.wealth || '--' }}</div>
          </div>
          <div class="bg-gray-800 rounded-lg p-3">
            <div class="text-xs text-gray-500">感情</div>
            <div class="text-lg font-bold text-amber-400">{{ result.consensus.relationships || '--' }}</div>
          </div>
          <div class="bg-gray-800 rounded-lg p-3">
            <div class="text-xs text-gray-500">健康</div>
            <div class="text-lg font-bold text-amber-400">{{ result.consensus.health || '--' }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { aiAnalyze } from '../api'

const loading = ref(false)
const error = ref('')
const result = ref(null)

const form = reactive({
  gender: 'male',
  date: '1990-01-01',
  time: '12:00',
  year: new Date().getFullYear(),
})

async function analyze() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await aiAnalyze({
      gender: form.gender,
      date: form.date,
      time: form.time,
      year: form.year,
    })
    result.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function clear() {
  result.value = null
  error.value = ''
}
</script>