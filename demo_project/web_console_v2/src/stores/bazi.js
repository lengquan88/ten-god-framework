import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useBaziStore = defineStore('bazi', () => {
  const result = ref(null)
  const loading = ref(false)
  const error = ref('')

  function setResult(data) { result.value = data }
  function clear() { result.value = null; error.value = '' }

  return { result, loading, error, setResult, clear }
})