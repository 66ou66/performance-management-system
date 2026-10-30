<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">数据看板</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ isElevated ? '专业师生业绩数据的整体概览，可直接下钻到明细' : '我的业绩成果汇总概览' }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <Select v-model="filterYear" @update:model-value="loadData">
          <SelectTrigger class="w-[120px]"><SelectValue placeholder="全部年份" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部年份</SelectItem>
            <SelectItem v-for="item in years" :key="item" :value="String(item)">{{ item }}</SelectItem>
          </SelectContent>
        </Select>

        <Select v-model="filterAcademicYear" @update:model-value="loadData">
          <SelectTrigger class="w-[130px]"><SelectValue placeholder="全部学年" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部学年</SelectItem>
            <SelectItem v-for="item in academicYears" :key="item" :value="String(item)">{{ item }}</SelectItem>
          </SelectContent>
        </Select>

        <Select v-if="isElevated" v-model="filterDepartment" @update:model-value="loadData">
          <SelectTrigger class="w-[140px]"><SelectValue placeholder="全部院系" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部院系</SelectItem>
            <SelectItem v-for="item in departments" :key="item" :value="String(item)">{{ item }}</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" :disabled="loading" @click="loadData">
          <RefreshCw class="size-4" :class="loading && 'animate-spin'" />
          刷新数据
        </Button>
      </div>
    </div>

    <!-- 指标卡片 -->
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" :class="loading && 'pointer-events-none opacity-60'">
      <button
        v-for="card in cards"
        :key="card.label"
        type="button"
        class="group flex items-center gap-3 rounded-xl border bg-white p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
        @click="drillDown(card)"
      >
        <span
          class="flex size-11 shrink-0 items-center justify-center rounded-lg"
          :style="{ background: card.color + '1f', color: card.color }"
        >
          <component :is="card.icon" class="size-5" />
        </span>
        <span>
          <span class="block text-2xl font-semibold leading-tight">{{ card.value }}</span>
          <span class="mt-0.5 block text-xs text-muted-foreground">{{ card.label }}</span>
        </span>
      </button>
    </div>

    <!-- 图表 -->
    <div class="grid gap-4 md:grid-cols-2">
      <Card v-for="chart in chartCards" :key="chart.title">
        <CardHeader>
          <CardTitle class="text-sm font-medium">{{ chart.title }}</CardTitle>
        </CardHeader>
        <CardContent>
          <EChart v-if="chart.data.length" :option="chart.option" height="300px" />
          <div v-else class="flex h-[300px] items-center justify-center text-sm text-muted-foreground">暂无数据</div>
        </CardContent>
      </Card>
    </div>

    <!-- 排行 -->
    <div v-if="isElevated" class="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader><CardTitle class="text-sm font-medium">教师成果排行 TOP10</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-12">#</TableHead>
                <TableHead>教师</TableHead>
                <TableHead class="w-24 text-right">成果数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, i) in teacherRanking" :key="row.name" class="cursor-pointer" @click="rankingClick(row)">
                <TableCell class="text-muted-foreground">{{ i + 1 }}</TableCell>
                <TableCell class="font-medium">{{ row.name }}</TableCell>
                <TableCell class="text-right">{{ row.value }}</TableCell>
              </TableRow>
              <TableEmpty v-if="!teacherRanking.length" :colspan="3">暂无数据</TableEmpty>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle class="text-sm font-medium">学生成果排行 TOP10</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-12">#</TableHead>
                <TableHead>学生</TableHead>
                <TableHead class="w-24 text-right">成果数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, i) in studentRanking" :key="row.name" class="cursor-pointer" @click="rankingClick(row)">
                <TableCell class="text-muted-foreground">{{ i + 1 }}</TableCell>
                <TableCell class="font-medium">{{ row.name }}</TableCell>
                <TableCell class="text-right">{{ row.value }}</TableCell>
              </TableRow>
              <TableEmpty v-if="!studentRanking.length" :colspan="3">暂无数据</TableEmpty>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>

    <!-- 最近业绩 -->
    <Card>
      <CardHeader class="flex-row items-center justify-between space-y-0">
        <CardTitle class="text-sm font-medium">最近业绩成果</CardTitle>
        <Button variant="link" class="h-auto p-0" @click="router.push('/achievements')">查看全部</Button>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>成果名称</TableHead>
              <TableHead>所属人</TableHead>
              <TableHead>成果类型</TableHead>
              <TableHead>级别</TableHead>
              <TableHead>年份</TableHead>
              <TableHead>材料</TableHead>
              <TableHead>录入时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in recent" :key="row.id">
              <TableCell class="max-w-[260px] truncate font-medium">{{ row.title }}</TableCell>
              <TableCell>
                {{ row.owner_name }}
                <Badge variant="outline" class="ml-1.5 text-xs font-normal text-muted-foreground">
                  {{ ownerTypeLabel(row.owner_type) }}
                </Badge>
              </TableCell>
              <TableCell>{{ row.category }}</TableCell>
              <TableCell>{{ row.level }}</TableCell>
              <TableCell>{{ row.year }}</TableCell>
              <TableCell>
                <Badge v-if="row.attachment_count" variant="secondary" class="text-emerald-600">已归档</Badge>
                <Badge v-else variant="secondary" class="text-destructive">缺材料</Badge>
              </TableCell>
              <TableCell class="text-muted-foreground">{{ row.created_at }}</TableCell>
            </TableRow>
            <TableEmpty v-if="!recent.length" :colspan="7">暂无成果数据</TableEmpty>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Award,
  FileText,
  FolderCheck,
  RefreshCw,
  TrendingUp,
  TriangleAlert,
  UserRound,
  Users
} from 'lucide-vue-next'
import EChart from '../components/EChart.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { achievementApi, metaApi, statsApi } from '../api'
import { useUserStore } from '../stores/user'
import { ownerTypeLabel } from '../utils/file'

const router = useRouter()
const userStore = useUserStore()
// 统一图表色板（与全局设计令牌配套，勿改动顺序）
const chartColors = ['#2563eb', '#00b2a9', '#7b61ff', '#f59e0b', '#ef4444', '#22c55e', '#38bdf8', '#ec4899']
const isElevated = computed(() => userStore.isElevated)

const loading = ref(false)
const counts = ref({})
const byCategory = ref([])
const byYear = ref([])
const byLevel = ref([])
const byDepartment = ref([])
const trend = ref([])
const teacherRanking = ref([])
const studentRanking = ref([])
const recent = ref([])

const filterYear = ref('__all__')
const filterAcademicYear = ref('__all__')
const filterDepartment = ref('__all__')
const years = ref([])
const academicYears = ref([])
const departments = ref([])

const filterParams = computed(() => {
  const params = {}
  if (filterYear.value && filterYear.value !== '__all__') params.year = filterYear.value
  if (filterAcademicYear.value && filterAcademicYear.value !== '__all__') params.academic_year = filterAcademicYear.value
  if (filterDepartment.value && filterDepartment.value !== '__all__') params.department = filterDepartment.value
  return params
})

const cards = computed(() => {
  const list = []
  if (isElevated.value) {
    list.push(
      { label: '教师总数', value: counts.value.teachers || 0, icon: UserRound, color: '#2563eb', path: '/teachers' },
      { label: '学生总数', value: counts.value.students || 0, icon: Users, color: '#13c2c2', path: '/students' }
    )
  }
  list.push(
    { label: '成果总数', value: counts.value.achievements || 0, icon: Award, color: '#6f4cf0', query: { ...filterParams.value } },
    { label: '本年度成果', value: counts.value.this_year || 0, icon: TrendingUp, color: '#e6a23c', query: { ...filterParams.value } },
    { label: '已归档材料成果', value: counts.value.attachments || 0, icon: FolderCheck, color: '#16a34a', query: { ...filterParams.value, has_attachment: '1' } },
    { label: '缺失材料成果', value: counts.value.missing_evidence || 0, icon: TriangleAlert, color: '#f43f5e', query: { ...filterParams.value, has_attachment: '0' } }
  )
  if (isElevated.value) {
    list.push({ label: '待审核成果', value: counts.value.pending || 0, icon: FileText, color: '#71717a', path: '/reviews' })
  }
  return list
})

const chartCards = computed(() => [
  { title: '成果类型分布', data: byCategory.value, option: pieOption.value },
  { title: '年度成果趋势（含同比）', data: trend.value, option: lineOption.value },
  { title: '成果级别分布', data: byLevel.value, option: levelOption.value },
  { title: '院系成果分布', data: byDepartment.value, option: departmentOption.value }
])

const pieOption = computed(() => ({
  color: chartColors,
  tooltip: { trigger: 'item', formatter: '{b}: {c} 项 ({d}%)' },
  legend: { type: 'scroll', bottom: 0, textStyle: { color: '#71717a', fontSize: 12 } },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{c}' },
      data: byCategory.value
    }
  ]
}))

const lineOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter: (params) => {
      const item = params[0]
      const row = trend.value[item.dataIndex] || {}
      const change = row.change_percent === null || row.change_percent === undefined ? '—' : `${row.change_percent}%`
      return `${item.name} 年<br/>成果数：${item.value}<br/>同比：${change}`
    }
  },
  grid: { left: 40, right: 20, top: 30, bottom: 40 },
  xAxis: { type: 'category', boundaryGap: false, data: trend.value.map((item) => item.name) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.18 },
      symbolSize: 8,
      data: trend.value.map((item) => item.value),
      itemStyle: { color: '#2563eb' }
    }
  ]
}))

const levelOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 50 },
  xAxis: { type: 'category', data: byLevel.value.map((item) => item.name), axisLabel: { interval: 0, rotate: 20 } },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    { type: 'bar', barMaxWidth: 38, data: byLevel.value.map((item) => item.value), itemStyle: { color: '#2563eb', borderRadius: [6, 6, 0, 0] } }
  ]
}))

const departmentOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 60 },
  xAxis: { type: 'category', data: byDepartment.value.map((item) => item.name), axisLabel: { interval: 0, rotate: 25 } },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    { type: 'bar', barMaxWidth: 38, data: byDepartment.value.map((item) => item.value), itemStyle: { color: '#00b2a9', borderRadius: [6, 6, 0, 0] } }
  ]
}))

async function loadMeta() {
  try {
    const data = await metaApi.options()
    years.value = data.years || []
    academicYears.value = data.academic_years || []
    departments.value = data.departments || []
  } catch (err) {
    // 统一错误处理
  }
}

async function loadData() {
  loading.value = true
  try {
    const [dashboard, list] = await Promise.all([
      statsApi.dashboard(filterParams.value),
      achievementApi.list({ page: 1, page_size: 5, ...filterParams.value })
    ])
    counts.value = dashboard.counts || {}
    byCategory.value = dashboard.by_category || []
    byYear.value = dashboard.by_year || []
    byLevel.value = dashboard.by_level || []
    byDepartment.value = dashboard.by_department || []
    trend.value = dashboard.trend || []
    teacherRanking.value = dashboard.teacher_ranking || []
    studentRanking.value = dashboard.student_ranking || []
    recent.value = list.items || []
  } catch (err) {
    // 错误提示已在请求拦截器中统一处理
  } finally {
    loading.value = false
  }
}

function drillDown(card) {
  if (card.path) {
    router.push(card.path)
    return
  }
  if (card.query) {
    router.push({ path: '/achievements', query: card.query })
  }
}

function rankingClick(row) {
  router.push({ path: '/achievements', query: { owner_name: row.name, ...filterParams.value } })
}

onMounted(() => {
  loadMeta()
  loadData()
})
</script>