<template>
  <div class="bg-gray-800 rounded-xl p-6">
    <h3 v-if="title" class="text-sm font-semibold text-gray-400 mb-4">{{ title }}</h3>
    <div v-if="dayuns?.length" class="relative">
      <div class="flex gap-2 overflow-x-auto pb-4">
        <div v-for="dy in dayuns" :key="dy.start_age"
          class="flex-shrink-0 w-24 bg-gray-750 rounded-lg p-3 text-center"
          :class="{ 'border border-amber-700/50': dy.start_age <= currentAge && dy.end_age >= currentAge }">
          <div class="text-xs text-gray-500">{{ dy.start_age }}-{{ dy.end_age }}岁</div>
          <div class="text-sm font-bold text-amber-400 mt-1">{{ dy.ganzhi }}</div>
          <div v-if="dy.shishen" class="text-xs text-gray-400 mt-0.5">{{ dy.shishen }}</div>
        </div>
      </div>
    </div>
    <div v-else class="text-center text-sm text-gray-600 py-4">暂无数据</div>
  </div>
</template>

<script setup>
defineProps({
  dayuns: { type: Array, default: () => [] },
  currentAge: { type: Number, default: 0 },
  title: { type: String, default: '' },
})
</script>