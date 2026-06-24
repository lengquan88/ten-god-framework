<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">紫微斗数</h1>

    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">出生信息</h2>
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
          <label class="block text-sm text-gray-400 mb-1">出生地点</label>
          <input v-model="form.place" class="input-field" placeholder="如：北京" />
        </div>
      </div>
      <div class="flex gap-3 mt-4">
        <button @click="calcZiwei" class="btn-primary" :disabled="loading">
          {{ loading ? '计算中...' : '开始排盘' }}
        </button>
        <button @click="clear" class="btn-secondary">清空</button>
      </div>
      <p v-if="error" class="mt-3 text-red-400 text-sm">{{ error }}</p>
    </div>

    <!-- 结果 -->
    <div v-if="result" class="space-y-6">
      <!-- 命宫 -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">命宫</h2>
        <div class="text-center">
          <div class="text-3xl font-bold text-amber-400">{{ result.ming_gong?.gong_name || '--' }}</div>
          <div class="text-sm text-gray-400 mt-1">地支：{{ result.ming_gong?.gong_zhi || '--' }}</div>
          <div v-if="result.ming_gong?.stars?.length" class="mt-2 flex justify-center flex-wrap gap-1">
            <span v-for="s in result.ming_gong.stars" :key="s.name || s" class="tag tag-active">
              {{ s.name || s }}
            </span>
          </div>
        </div>
      </div>

      <!-- 十二宫 -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">十二宫位</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <div v-for="p in result.palaces" :key="p.gong_name"
            class="bg-gray-800 rounded-lg p-3">
            <div class="text-sm font-medium text-amber-400">{{ p.gong_name }}</div>
            <div class="text-xs text-gray-500">{{ p.gong_zhi }}</div>
            <div v-if="p.stars?.length" class="mt-1 flex flex-wrap gap-1">
              <span v-for="s in p.stars.slice(0, 3)" :key="s.name || s" class="text-xs text-gray-400">
                {{ s.name || s }}
              </span>
            </div>
            <div v-if="!p.stars?.length" class="text-xs text-gray-600 mt-1">空宫</div>
          </div>
        </div>
      </div>

      <!-- 四化 -->
      <div v-if="result.sihua" class="card">
        <h2 class="text-lg font-semibold mb-4">四化飞星</h2>
        <div class="grid grid-cols-4 gap-3 text-center">
          <div v-for="(v, k) in result.sihua" :key="k" class="bg-gray-800 rounded-lg p-3">
            <div class="text-sm text-gray-400">{{ k }}</div>
            <div class="text-lg font-bold text-amber-400">{{ v }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { calcZiwei as apiCalcZiwei } from '../api'

const loading = ref(false)
const error = ref('')
const result = ref(null)

const form = reactive({
  gender: 'male',
  date: '1990-01-01',
  time: '12:00',
  place: '北京',
})

async function calcZiwei() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiCalcZiwei({
      gender: form.gender,
      date: form.date,
      time: form.time,
      place: form.place,
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