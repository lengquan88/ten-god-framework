import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getHealth, getDbStats } from '../api'

export const useAppStore = defineStore('app', () => {
  const systemStatus = ref({ status: 'loading' })
  const dbStats = ref(null)
  const loading = ref(false)
  const error = ref('')

  const isOnline = computed(() => systemStatus.value?.status === 'healthy')

  async function fetchHealth() {
    try {
      const { data } = await getHealth()
      systemStatus.value = data
    } catch {
      systemStatus.value = { status: 'offline' }
    }
  }

  async function fetchDbStats() {
    try {
      const { data } = await getDbStats()
      dbStats.value = data
    } catch {
      dbStats.value = null
    }
  }

  return { systemStatus, dbStats, loading, error, isOnline, fetchHealth, fetchDbStats }
})