<template>
  <div class="bg-gray-800 rounded-xl p-6">
    <h3 v-if="title" class="text-sm font-semibold text-gray-400 mb-4">{{ title }}</h3>
    <div v-if="hasData" class="w-full max-w-xs mx-auto" style="aspect-ratio: 1">
      <svg viewBox="-100 -100 200 200" class="w-full h-full">
        <polygon
          v-for="(pt, i) in polygonPoints"
          :key="i"
          :points="pt"
          :fill="colors[i]"
          :opacity="0.3"
          :stroke="colors[i]"
          stroke-width="1.5"
        />
        <!-- 轴 -->
        <line v-for="(_, i) in 5" :key="'axis-' + i"
          :x1="0" :y1="0"
          :x2="axisPoints[i].x"
          :y2="axisPoints[i].y"
          stroke="#333" stroke-width="0.5" />
        <!-- 标签 -->
        <text v-for="(lbl, i) in labels" :key="'lbl-' + i"
          :x="axisPoints[i].x * 1.2"
          :y="axisPoints[i].y * 1.2"
          text-anchor="middle" dominant-baseline="middle"
          fill="#888" font-size="12">
          {{ lbl }}
        </text>
      </svg>
    </div>
    <div v-else class="text-center text-sm text-gray-600 py-4">暂无数据</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  title: { type: String, default: '' },
})

const wuxingOrder = ['金', '木', '水', '火', '土']
const colors = ['#fbbf24', '#34d399', '#60a5fa', '#f87171', '#a78bfa']

const labels = computed(() => wuxingOrder)

const hasData = computed(() => {
  return wuxingOrder.some(w => (props.data?.[w] || 0) > 0)
})

const values = computed(() => {
  return wuxingOrder.map(w => props.data?.[w] || 0)
})

const maxVal = computed(() => Math.max(1, ...values.value))

const axisPoints = computed(() => {
  return wuxingOrder.map((_, i) => {
    const angle = (Math.PI * 2 / 5) * i - Math.PI / 2
    const r = 80
    return { x: Math.cos(angle) * r, y: Math.sin(angle) * r }
  })
})

const polygonPoints = computed(() => {
  const pts = values.value.map((v, i) => {
    const angle = (Math.PI * 2 / 5) * i - Math.PI / 2
    const r = (v / maxVal.value) * 80
    return `${Math.cos(angle) * r},${Math.sin(angle) * r}`
  })
  return [pts.join(' ')]
})
</script>