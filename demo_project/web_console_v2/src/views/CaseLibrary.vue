<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">案例库</h1>
      <div class="flex gap-2">
        <button @click="fetchCases" class="btn-secondary" :disabled="loading">刷新</button>
        <button @click="showImport = true" class="btn-secondary">导入</button>
        <button @click="exportCases" class="btn-primary">导出</button>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="card mb-6">
      <div class="flex flex-wrap gap-3">
        <input v-model="search" @keyup.enter="fetchCases" class="input-field flex-1 min-w-200px"
          placeholder="搜索案例名称、八字信息..." />
        <select v-model="category" @change="fetchCases" class="input-field w-32">
          <option value="">全部分类</option>
          <option value="bazi">八字</option>
          <option value="ziwei">紫微</option>
          <option value="qimen">奇门</option>
          <option value="liuyao">六爻</option>
          <option value="general">综合</option>
        </select>
        <button @click="fetchCases" class="btn-primary" :disabled="loading">搜索</button>
      </div>
    </div>

    <!-- 列表 -->
    <div v-if="loading" class="text-center py-12 text-gray-500">加载中...</div>
    <div v-else-if="items.length === 0" class="text-center py-12 text-gray-500">暂无案例数据</div>
    <div v-else class="space-y-3">
      <div v-for="item in items" :key="item.id"
        class="card card-hover flex items-start justify-between">
        <div class="flex-1">
          <h3 class="font-medium text-amber-400">{{ item.name }}</h3>
          <div class="flex gap-2 mt-1">
            <span class="tag">{{ item.category }}</span>
            <span v-for="t in item.tags?.slice(0, 3)" :key="t" class="tag">{{ t }}</span>
          </div>
          <p v-if="item.analysis?.summary" class="text-sm text-gray-400 mt-2 line-clamp-2">
            {{ item.analysis.summary }}
          </p>
        </div>
        <button @click="deleteCaseItem(item.id)" class="btn-danger !px-2 !py-1 text-xs ml-3">删除</button>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center gap-2 mt-6">
      <button @click="page--; fetchCases()" :disabled="page <= 1" class="btn-secondary">上一页</button>
      <span class="flex items-center px-4 text-sm text-gray-400">{{ page }} / {{ totalPages }}</span>
      <button @click="page++; fetchCases()" :disabled="page >= totalPages" class="btn-secondary">下一页</button>
    </div>

    <!-- 导入弹窗 -->
    <div v-if="showImport" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div class="card w-full max-w-md">
        <h3 class="text-lg font-semibold mb-4">导入案例</h3>
        <textarea v-model="importJson" class="input-field h-40" placeholder="粘贴 JSON 数据..."></textarea>
        <div class="flex gap-2 mt-4 justify-end">
          <button @click="showImport = false" class="btn-secondary">取消</button>
          <button @click="doImport" class="btn-primary" :disabled="!importJson">导入</button>
        </div>
        <p v-if="importMsg" class="mt-2 text-sm" :class="importError ? 'text-red-400' : 'text-green-400'">{{ importMsg }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listCases, deleteCase, exportCases as apiExport, importCases } from '../api'

const items = ref([])
const loading = ref(false)
const search = ref('')
const category = ref('')
const page = ref(1)
const totalPages = ref(1)
const showImport = ref(false)
const importJson = ref('')
const importMsg = ref('')
const importError = ref(false)

async function fetchCases() {
  loading.value = true
  try {
    const { data } = await listCases({
      page: page.value,
      page_size: 20,
      category: category.value,
      search: search.value,
    })
    items.value = data.items || []
    totalPages.value = data.total_pages || 1
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function deleteCaseItem(id) {
  if (!confirm('确认删除此案例？')) return
  try {
    await deleteCase(id)
    items.value = items.value.filter(i => i.id !== id)
  } catch (e) {
    alert('删除失败：' + e.message)
  }
}

async function exportCases() {
  try {
    const { data } = await apiExport()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cases_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('导出失败：' + e.message)
  }
}

async function doImport() {
  try {
    const parsed = JSON.parse(importJson.value)
    await importCases(parsed)
    importMsg.value = '导入成功'
    importError.value = false
    showImport.value = false
    importJson.value = ''
    fetchCases()
  } catch (e) {
    importMsg.value = '导入失败：' + e.message
    importError.value = true
  }
}

onMounted(fetchCases)
</script>