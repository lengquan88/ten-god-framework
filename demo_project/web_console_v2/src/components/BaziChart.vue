<template>
  <div class="bg-gray-800 rounded-xl p-6">
    <h3 v-if="title" class="text-sm font-semibold text-gray-400 mb-3">{{ title }}</h3>
    <div class="grid grid-cols-4 gap-4 text-center">
      <div v-for="p in pillars" :key="p.key" class="bg-gray-750 rounded-lg p-3">
        <div class="text-xs text-gray-500">{{ p.label }}</div>
        <div class="text-xl font-bold text-amber-400">{{ p.ganzhi }}</div>
        <div v-if="p.shigan" class="text-xs text-gray-400 mt-1">{{ p.shigan }}</div>
        <div v-if="p.canggan" class="text-xs text-gray-500 mt-0.5">{{ p.canggan }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  title: { type: String, default: '' },
})

const pillars = computed(() => {
  const labels = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' }
  if (!props.data?.pillars) return []
  return Object.entries(props.data.pillars).map(([k, v]) => ({
    key: k,
    label: labels[k] || k,
    ganzhi: v,
    shigan: props.data.shigan_map?.[`${k}_gan`] || '',
    canggan: props.data.canggan_map?.[`${k}_zhi`] || '',
  }))
})
</script>