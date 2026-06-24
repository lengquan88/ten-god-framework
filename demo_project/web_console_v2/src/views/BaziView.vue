<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">八字排盘</h1>

    <!-- 输入表单 -->
    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">出生信息</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">姓名</label>
          <input v-model="form.name" class="input-field" placeholder="请输入姓名" />
        </div>
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
      </div>
      <div class="flex gap-3 mt-4">
        <button @click="calcBazi" class="btn-primary" :disabled="loading">
          {{ loading ? '计算中...' : '开始排盘' }}
        </button>
        <button @click="clear" class="btn-secondary">清空</button>
      </div>
      <p v-if="error" class="mt-3 text-red-400 text-sm">{{ error }}</p>
    </div>

    <!-- 结果展示 -->
    <div v-if="result" class="space-y-6">
      <!-- 四柱 -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">四柱八字</h2>
        <div class="grid grid-cols-4 gap-4 text-center">
          <div v-for="p in pillars" :key="p.key" class="bg-gray-800 rounded-lg p-4">
            <div class="text-xs text-gray-500 mb-1">{{ p.label }}</div>
            <div class="text-2xl font-bold text-amber-400">{{ p.ganzhi }}</div>
            <div v-if="p.shigan" class="text-xs text-gray-400 mt-1">{{ p.shigan }}</div>
          </div>
        </div>
        <div class="mt-4 text-center">
          <span class="text-sm text-gray-400">日主：</span>
          <span class="text-lg font-bold text-amber-400">{{ result.day_master }}</span>
        </div>
      </div>

      <!-- 五行分布 -->
      <div v-if="result.wuxing" class="card">
        <h2 class="text-lg font-semibold mb-4">五行分布</h2>
        <div class="grid grid-cols-5 gap-3">
          <div v-for="(count, wx) in wuxingColors" :key="wx" class="text-center">
            <div class="text-sm text-gray-400">{{ wx }}</div>
            <div class="w-full bg-gray-800 rounded-full h-3 mt-1">
              <div class="h-3 rounded-full transition-all duration-500"
                :style="{ width: ((result.wuxing[wx] || 0) / maxWuxing * 100) + '%', backgroundColor: count.color }" />
            </div>
            <div class="text-xs text-gray-500 mt-1">{{ result.wuxing[wx] || 0 }}</div>
          </div>
        </div>
      </div>

      <!-- 格局与喜用神 -->
      <div v-if="result.geju || result.yongshen" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div v-if="result.geju" class="card">
          <h2 class="text-lg font-semibold mb-3">格局</h2>
          <div class="text-amber-400 font-bold text-lg">{{ result.geju?.geju_name || '--' }}</div>
          <div class="text-sm text-gray-400 mt-1">{{ result.geju?.geju_desc || '' }}</div>
        </div>
        <div v-if="result.yongshen" class="card">
          <h2 class="text-lg font-semibold mb-3">喜用神</h2>
          <div class="flex gap-3">
            <div>
              <span class="text-sm text-gray-400">喜用：</span>
              <span class="text-green-400 font-bold">{{ (result.yongshen?.yong_shen || []).join('、') }}</span>
            </div>
            <div>
              <span class="text-sm text-gray-400">忌：</span>
              <span class="text-red-400 font-bold">{{ (result.yongshen?.ji_shen || []).join('、') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 神煞 -->
      <div v-if="result.shensha" class="card">
        <h2 class="text-lg font-semibold mb-4">神煞</h2>
        <div v-for="(shens, pillar) in flatShensha" :key="pillar"
          class="mb-2 last:mb-0">
          <span class="text-sm text-gray-400">{{ pillar }}：</span>
          <span v-for="s in shens" :key="s" class="tag ml-1" :class="{ 'tag-active': s.includes('吉') }">{{ s }}</span>
        </div>
      </div>

      <!-- 大运 -->
      <div v-if="result.dayuns" class="card">
        <h2 class="text-lg font-semibold mb-4">大运流年</h2>
        <div class="flex flex-wrap gap-2">
          <div v-for="dy in result.dayuns.slice(0, 8)" :key="dy.start_age"
            class="bg-gray-800 rounded-lg px-3 py-2 text-sm">
            <span class="text-gray-400">{{ dy.start_age }}-{{ dy.end_age }}岁</span>
            <span class="text-amber-400 ml-2 font-bold">{{ dy.ganzhi }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { calcFullBazi } from '../api'
import { useBaziStore } from '../stores/bazi'

const store = useBaziStore()
const loading = ref(false)
const error = ref('')
const result = ref(null)

const form = reactive({
  name: '',
  gender: 'male',
  date: '1990-01-01',
  time: '12:00',
})

const wuxingColors = {
  '金': { color: '#fbbf24' },
  '木': { color: '#34d399' },
  '水': { color: '#60a5fa' },
  '火': { color: '#f87171' },
  '土': { color: '#a78bfa' },
}

const maxWuxing = computed(() => {
  if (!result.value?.wuxing) return 1
  return Math.max(1, ...Object.values(result.value.wuxing))
})

const pillars = computed(() => {
  if (!result.value?.pillars) return []
  const labels = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' }
  return Object.entries(result.value.pillars).map(([k, v]) => ({
    key: k, label: labels[k] || k, ganzhi: v,
    shigan: result.value.shigan_map?.[`${k}_gan`] || '',
  }))
})

const flatShensha = computed(() => {
  if (!result.value?.shensha) return {}
  const out = {}
  for (const [k, v] of Object.entries(result.value.shensha)) {
    const label = k.replace('_shens', '').replace('year', '年柱').replace('month', '月柱')
      .replace('day', '日柱').replace('hour', '时柱')
    if (v && typeof v === 'object') {
      out[label] = Object.keys(v)
    }
  }
  return out
})

async function calcBazi() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await calcFullBazi({
      name: form.name,
      gender: form.gender,
      date: form.date,
      time: form.time,
    })
    result.value = data
    store.setResult(data)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function clear() {
  result.value = null
  error.value = ''
  store.clear()
}
</script>