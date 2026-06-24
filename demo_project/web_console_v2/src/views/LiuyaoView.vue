<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">六爻占卜</h1>

    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">起卦</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">所问之事</label>
          <input v-model="form.question" class="input-field" placeholder="请输入你想问的事情" />
        </div>
        <div class="flex items-end">
          <button @click="castLiuyao" class="btn-primary w-full" :disabled="loading">
            {{ loading ? '起卦中...' : '摇卦' }}
          </button>
        </div>
      </div>
      <p v-if="error" class="mt-3 text-red-400 text-sm">{{ error }}</p>
    </div>

    <div v-if="result" class="space-y-6">
      <!-- 卦象 -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">卦象</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
          <div class="bg-gray-800 rounded-lg p-4">
            <div class="text-sm text-gray-400">本卦</div>
            <div class="text-2xl font-bold text-amber-400 mt-1">{{ result.ben_gua_name }}</div>
            <div class="text-3xl mt-2">{{ result.ben_gua_symbol }}</div>
          </div>
          <div v-if="result.bian_gua_name" class="bg-gray-800 rounded-lg p-4">
            <div class="text-sm text-gray-400">变卦</div>
            <div class="text-2xl font-bold text-amber-400 mt-1">{{ result.bian_gua_name }}</div>
            <div class="text-3xl mt-2">{{ result.bian_gua_symbol }}</div>
          </div>
          <div v-if="result.hu_gua_name" class="bg-gray-800 rounded-lg p-4">
            <div class="text-sm text-gray-400">互卦</div>
            <div class="text-2xl font-bold text-amber-400 mt-1">{{ result.hu_gua_name }}</div>
          </div>
        </div>
      </div>

      <!-- 六爻详情 -->
      <div class="card">
        <h2 class="text-lg font-semibold mb-4">六爻详情</h2>
        <div class="space-y-2">
          <div v-for="(_, i) in 6" :key="i"
            class="flex items-center gap-4 bg-gray-800 rounded-lg p-3"
            :class="{ 'border border-amber-700/50': isDongYao(5 - i) }">
            <span class="text-xs text-gray-500 w-6">{{ ['初', '二', '三', '四', '五', '上'][i] }}爻</span>
            <span class="text-sm font-mono text-gray-300">{{ result.liuqin?.[5 - i] || '--' }}</span>
            <span class="text-xs text-gray-500">{{ result.liushen?.[5 - i] || '--' }}</span>
            <span v-if="isDongYao(5 - i)" class="tag tag-active text-xs">动</span>
            <span v-if="result.shi_yao === String(5 - i + 1)" class="tag text-xs">世</span>
            <span v-if="result.ying_yao === String(5 - i + 1)" class="tag text-xs">应</span>
          </div>
        </div>
      </div>

      <!-- 断辞 -->
      <div v-if="result.duan_ci" class="card">
        <h2 class="text-lg font-semibold mb-4">断辞</h2>
        <p class="text-gray-300 leading-relaxed">{{ result.duan_ci }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { castLiuyao as apiCast } from '../api'

const loading = ref(false)
const error = ref('')
const result = ref(null)

const form = reactive({ question: '' })

function isDongYao(idx) {
  return result.value?.dong_yao?.includes(idx)
}

async function castLiuyao() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiCast({
      question: form.question,
      date: new Date().toISOString().slice(0, 10),
    })
    result.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>