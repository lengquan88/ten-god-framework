<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">奇门遁甲</h1>

    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">起局参数</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">日期时间</label>
          <input v-model="form.datetime" type="datetime-local" class="input-field" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">所问之事</label>
          <input v-model="form.question" class="input-field" placeholder="如：事业发展" />
        </div>
        <div class="flex items-end">
          <button @click="castQimen" class="btn-primary w-full" :disabled="loading">
            {{ loading ? '计算中...' : '起局' }}
          </button>
        </div>
      </div>
      <p v-if="error" class="mt-3 text-red-400 text-sm">{{ error }}</p>
    </div>

    <!-- 九宫格 -->
    <div v-if="result" class="space-y-6">
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">奇门九宫盘</h2>
        <div class="grid grid-cols-3 gap-2 max-w-lg mx-auto">
          <div v-for="i in 9" :key="i"
            class="aspect-square bg-gray-800 rounded-lg p-2 flex flex-col items-center justify-center text-center"
            :class="{
              'opacity-0': i === 5 && !result.gongs?.[4],
              'border border-amber-700/50': i === 5 && result.gongs?.[4]
            }">
            <template v-if="result.gongs?.[i - 1]">
              <div class="text-xs text-gray-500">{{ result.gongs[i - 1].name || '' }}</div>
              <div class="text-sm font-bold text-amber-400">{{ result.gongs[i - 1].men || '' }}</div>
              <div class="text-xs text-gray-400">{{ result.gongs[i - 1].xing || '' }}</div>
              <div class="text-xs text-gray-400">{{ result.gongs[i - 1].shen || '' }}</div>
            </template>
          </div>
        </div>
      </div>

      <!-- 详情 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="card">
          <h3 class="text-sm font-semibold text-gray-400 mb-2">八门</h3>
          <div class="flex flex-wrap gap-1">
            <span v-for="m in result.men" :key="m" class="tag tag-active">{{ m }}</span>
          </div>
        </div>
        <div class="card">
          <h3 class="text-sm font-semibold text-gray-400 mb-2">九星</h3>
          <div class="flex flex-wrap gap-1">
            <span v-for="x in result.xing" :key="x" class="tag">{{ x }}</span>
          </div>
        </div>
        <div class="card">
          <h3 class="text-sm font-semibold text-gray-400 mb-2">八神</h3>
          <div class="flex flex-wrap gap-1">
            <span v-for="s in result.shen" :key="s" class="tag">{{ s }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { calcQimen } from '../api'

const loading = ref(false)
const error = ref('')
const result = ref(null)

const form = reactive({
  datetime: new Date().toISOString().slice(0, 16),
  question: '',
})

async function castQimen() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await calcQimen({
      datetime: form.datetime,
      question: form.question,
    })
    result.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>