<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">系统设置</h1>

    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">认证</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">用户名</label>
          <input v-model="auth.username" class="input-field" placeholder="admin" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">密码</label>
          <input v-model="auth.password" type="password" class="input-field" placeholder="••••••" />
        </div>
      </div>
      <div class="flex gap-3 mt-4">
        <button @click="doLogin" class="btn-primary" :disabled="loginLoading">
          {{ loginLoading ? '登录中...' : '登录' }}
        </button>
        <button @click="doLogout" class="btn-secondary">退出</button>
      </div>
      <p v-if="authMsg" class="mt-3 text-sm" :class="authError ? 'text-red-400' : 'text-green-400'">{{ authMsg }}</p>
    </div>

    <div class="card mb-6">
      <h2 class="text-lg font-semibold mb-4">API 配置</h2>
      <div>
        <label class="block text-sm text-gray-400 mb-1">API 地址</label>
        <input v-model="apiBase" class="input-field" placeholder="/api" />
      </div>
      <div class="mt-3">
        <label class="block text-sm text-gray-400 mb-1">Token</label>
        <div class="flex gap-2">
          <input v-model="token" class="input-field flex-1" placeholder="Bearer token..." readonly />
          <button @click="copyToken" class="btn-secondary">复制</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h2 class="text-lg font-semibold mb-4">关于</h2>
      <div class="space-y-2 text-sm text-gray-400">
        <div class="flex justify-between"><span>版本</span><span class="text-gray-300">v2.13.0</span></div>
        <div class="flex justify-between"><span>框架</span><span class="text-gray-300">Vue 3 + Vite + Tailwind CSS</span></div>
        <div class="flex justify-between"><span>后端</span><span class="text-gray-300">FastAPI + SQLite</span></div>
        <div class="flex justify-between"><span>项目</span><span class="text-gray-300">中华文明数字永生体</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { login } from '../api'

const auth = ref({ username: '', password: '' })
const loginLoading = ref(false)
const authMsg = ref('')
const authError = ref(false)
const apiBase = ref('/api')
const token = ref(localStorage.getItem('tengod_token') || '')

async function doLogin() {
  loginLoading.value = true
  authMsg.value = ''
  try {
    const { data } = await login({ username: auth.value.username, password: auth.value.password })
    localStorage.setItem('tengod_token', data.access_token)
    token.value = data.access_token
    authMsg.value = '登录成功'
    authError.value = false
  } catch (e) {
    authMsg.value = e.message
    authError.value = true
  } finally {
    loginLoading.value = false
  }
}

function doLogout() {
  localStorage.removeItem('tengod_token')
  token.value = ''
  authMsg.value = '已退出'
  authError.value = false
}

function copyToken() {
  navigator.clipboard.writeText(token.value)
}
</script>