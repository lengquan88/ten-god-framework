<template>
  <div class="bg-gray-900 rounded-lg p-3 border border-gray-800 hover:border-gray-700 transition-colors">
    <div class="text-xs text-gray-500 mb-1">{{ label }}</div>
    <div class="text-lg font-semibold" :class="colorClass">{{ value }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  color: { type: String, default: 'gray' },
})

const colorMap = {
  blue: 'text-blue-400',
  red: 'text-red-400',
  green: 'text-green-400',
  amber: 'text-amber-400',
  purple: 'text-purple-400',
  gray: 'text-gray-400',
}

const colorClass = computed(() => colorMap[props.color] || colorMap.gray)
</script>