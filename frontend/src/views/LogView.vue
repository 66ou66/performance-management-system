<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">操作日志审计</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          记录登录、录入、修改、删除、审核、导入导出等关键操作，用于认证材料的可追溯性核查
        </p>
      </div>
      <Button variant="outline" @click="loadList"><RefreshCw class="size-4" /> 刷新</Button>
    </div>

    <!-- 趋势图 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div ref="chartRef" class="h-[220px]" />
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">操作类型</Label>
          <Select v-model="filters.action">
            <SelectTrigger class="w-[150px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in actions" :key="item.value" :value="item.value">{{ item.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">对象</Label>
          <Select v-model="filters.target_type">
            <SelectTrigger class="w-[130px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in targets" :key="item.value" :value="item.value">{{ item.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">操作人</Label>
          <Input v-model="filters.username" placeholder="登录名" class="w-[130px]" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">关键词</Label>
          <Input v-model="filters.keyword" placeholder="描述内容" class="w-[180px]" @keyup.enter="handleSearch" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">开始日期</Label>
          <Input v-model="startDate" type="date" class="w-[150px]" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">结束日期</Label>
          <Input v-model="endDate" type="date" class="w-[150px]" />
        </div>
        <div class="flex gap-2">
          <Button @click="handleSearch"><Search class="size-4" /> 查询</Button>
          <Button variant="outline" @click="handleReset"><RotateCcw class="size-4" /> 重置</Button>
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[170px]">时间</TableHead>
            <TableHead class="w-[120px]">操作人</TableHead>
            <TableHead class="w-[120px]">操作</TableHead>
            <TableHead class="w-[100px]">对象</TableHead>
            <TableHead>描述</TableHead>
            <TableHead class="w-[130px]">IP</TableHead>
            <TableHead class="w-[90px] text-right">详情</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell class="text-muted-foreground">{{ row.created_at }}</TableCell>
            <TableCell>{{ row.username || '系统' }}</TableCell>
            <TableCell>
              <Badge variant="secondary">{{ actionLabel(row.action) }}</Badge>
            </TableCell>
            <TableCell>{{ targetLabel(row.target_type) }}</TableCell>
            <TableCell class="max-w-[280px] truncate text-muted-foreground">{{ row.summary }}</TableCell>
            <TableCell class="text-muted-foreground">{{ row.ip }}</TableCell>
            <TableCell class="text-right">
              <Button v-if="row.detail" variant="ghost" size="sm" @click="openDetail(row)">查看</Button>
              <span v-else class="text-muted-foreground">-</span>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="7">暂无日志</TableEmpty>
        </TableBody>
      </Table>

      <div class="border-t px-4 py-3">
        <AppPagination :total="total" :page="page" :page-size="pageSize" :page-sizes="[20, 50, 100]" @change="onPageChange" />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <Dialog v-model:open="detailVisible">
      <DialogContent class="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>操作详情</DialogTitle>
        </DialogHeader>
        <pre class="max-h-[420px] overflow-auto rounded-md bg-zinc-50 p-3 text-xs">{{ detailText }}</pre>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RotateCcw, RefreshCw, Search } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { logApi } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const actions = ref([])
const targets = ref([])
const startDate = ref('')
const endDate = ref('')
const detailVisible = ref(false)
const detailRow = ref(null)
const chartRef = ref(null)
let chart = null

const filters = reactive({ action: '__all__', target_type: '__all__', username: '', keyword: '' })

const detailText = computed(() => {
  if (!detailRow.value || !detailRow.value.detail) return ''
  try {
    return JSON.stringify(detailRow.value.detail, null, 2)
  } catch (err) {
    return String(detailRow.value.detail)
  }
})

function actionLabel(value) {
  const found = actions.value.find((item) => item.value === value)
  return found ? found.label : value
}

function targetLabel(value) {
  const found = targets.value.find((item) => item.value === value)
  return found ? found.label : value || '-'
}

async function loadOptions() {
  try {
    const data = await logApi.options()
    actions.value = data.actions || []
    targets.value = data.targets || []
  } catch (err) {
    // 统一错误处理
  }
}

async function loadChart() {
  try {
    const data = await logApi.summary()
    const { default: echarts } = await import('echarts/core')
    const { BarChart } = await import('echarts/charts')
    const { GridComponent, TooltipComponent } = await import('echarts/components')
    const { CanvasRenderer } = await import('echarts/renderers')
    echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
    if (!chartRef.value) return
    if (!chart) chart = echarts.init(chartRef.value)
    chart.setOption({
      title: { text: '近 14 天操作趋势', left: 0, textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 50, bottom: 30 },
      xAxis: { type: 'category', data: (data.daily || []).map((item) => item.name) },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar',
        data: (data.daily || []).map((item) => item.value),
        itemStyle: { color: '#409eff' }
      }]
    })
  } catch (err) {
    // 图表失败不影响列表
  }
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.keys(filters).forEach((key) => {
      if (filters[key] && filters[key] !== '__all__') params[key] = filters[key]
    })
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value
    const data = await logApi.list(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function onPageChange({ page: p, pageSize: ps }) {
  page.value = p
  pageSize.value = ps
  loadList()
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  Object.keys(filters).forEach((key) => {
    filters[key] = ''
  })
  filters.action = '__all__'
  filters.target_type = '__all__'
  startDate.value = ''
  endDate.value = ''
  page.value = 1
  loadList()
}

function openDetail(row) {
  detailRow.value = row
  detailVisible.value = true
}

onMounted(() => {
  loadOptions()
  loadList()
  loadChart()
})
</script>