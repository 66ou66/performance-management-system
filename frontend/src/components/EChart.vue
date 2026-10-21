<template>
  <div ref="chartRef" class="chart-box" :style="{ height }"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
// 按需引入：只打包实际用到的图表与组件，避免把整个 echarts 打进产物
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, RadarChart } from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  RadarChart,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
  CanvasRenderer
])

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '300px' }
})

const chartRef = ref(null)
let chart = null
let observer = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  render()
  observer = new ResizeObserver(() => {
    if (chart) chart.resize()
  })
  observer.observe(chartRef.value)
})

watch(
  () => props.option,
  () => render(),
  { deep: true }
)

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  if (chart) chart.dispose()
  chart = null
})
</script>

<style scoped>
.chart-box {
  width: 100%;
}
</style>