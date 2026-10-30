<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">统计报表</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          按成果类型、年度、级别、院系、学年、状态多维度统计，支持交叉分析与认证指标点覆盖率
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button variant="outline" :disabled="exportingMissing" @click="handleExportMissing">
          <FileText class="size-4" /> 导出缺件清单
        </Button>
        <Button variant="outline" :disabled="exportingPackage" @click="handleExportPackage">
          <FolderOpen class="size-4" /> 导出佐证材料包
        </Button>
        <Button v-if="isElevated" :disabled="exporting" @click="handleExport">
          <Download class="size-4" /> 导出统计报表
        </Button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">年份</Label>
          <Select v-model="filters.year" @update:model-value="loadAll">
            <SelectTrigger class="w-[110px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in years" :key="item" :value="String(item)">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">学年</Label>
          <Select v-model="filters.academic_year" @update:model-value="loadAll">
            <SelectTrigger class="w-[130px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in academicYears" :key="item" :value="String(item)">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">院系</Label>
          <Select v-model="filters.department" @update:model-value="loadAll">
            <SelectTrigger class="w-[150px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in departments" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div v-if="isElevated" class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">人员类型</Label>
          <Select v-model="filters.owner_type" @update:model-value="loadAll">
            <SelectTrigger class="w-[110px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem value="teacher">教师</SelectItem>
              <SelectItem value="student">学生</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div v-if="isElevated" class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">统计口径</Label>
          <Select v-model="filters.status" @update:model-value="loadAll">
            <SelectTrigger class="w-[130px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="approved">仅已通过</SelectItem>
              <SelectItem value="pending">待审核</SelectItem>
              <SelectItem value="draft">草稿</SelectItem>
              <SelectItem value="rejected">已驳回</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" @click="handleReset"><RotateCcw class="size-4" /> 重置</Button>
      </div>
    </div>

    <!-- 统计卡 -->
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <div class="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm">
        <div class="grid size-11 shrink-0 place-items-center rounded-lg" style="background: #6f4cf01f; color: #6f4cf0"><Award class="size-5" /></div>
        <div><div class="text-2xl font-semibold leading-tight">{{ counts.achievements || 0 }}</div><div class="mt-0.5 text-xs text-muted-foreground">成果总数</div></div>
      </div>
      <div class="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm">
        <div class="grid size-11 shrink-0 place-items-center rounded-lg" style="background: #67c23a1f; color: #67c23a"><FileText class="size-5" /></div>
        <div><div class="text-2xl font-semibold leading-tight">{{ counts.attachments || 0 }}</div><div class="mt-0.5 text-xs text-muted-foreground">已归档材料</div></div>
      </div>
      <div class="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm">
        <div class="grid size-11 shrink-0 place-items-center rounded-lg" style="background: #f56c6c1f; color: #f56c6c"><TriangleAlert class="size-5" /></div>
        <div><div class="text-2xl font-semibold leading-tight">{{ counts.missing_evidence || 0 }}</div><div class="mt-0.5 text-xs text-muted-foreground">缺少材料</div></div>
      </div>
      <div class="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm">
        <div class="grid size-11 shrink-0 place-items-center rounded-lg" style="background: #e6a23c1f; color: #e6a23c"><TrendingUp class="size-5" /></div>
        <div><div class="text-2xl font-semibold leading-tight">{{ counts.this_year || 0 }}</div><div class="mt-0.5 text-xs text-muted-foreground">本年度成果</div></div>
      </div>
      <div v-if="coverage" class="flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm">
        <div class="grid size-11 shrink-0 place-items-center rounded-lg" style="background: #2f6feb1f; color: #2f6feb"><BarChart3 class="size-5" /></div>
        <div><div class="text-2xl font-semibold leading-tight">{{ coverage.coverage_percent }}%</div><div class="mt-0.5 text-xs text-muted-foreground">指标点覆盖率</div></div>
      </div>
    </div>

    <!-- 分布图 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div class="inline-flex flex-wrap items-center gap-1 rounded-lg border bg-muted p-1">
          <Button
            v-for="item in dimensions"
            :key="item.value"
            :variant="dimension === item.value ? 'default' : 'ghost'"
            size="sm"
            @click="dimension = item.value; loadBreakdown()"
          >
            {{ item.label }}
          </Button>
        </div>
        <span class="text-sm text-muted-foreground">统计维度：{{ currentDimensionLabel }}，共 {{ total }} 条</span>
      </div>
      <EChart v-if="items.length" :option="chartOption" height="360px" />
      <div v-else class="py-12 text-center text-sm text-muted-foreground">暂无统计数据</div>
    </div>

    <!-- 分布表 + 交叉分析 -->
    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-xl border bg-white shadow-sm">
        <div class="border-b px-4 py-3 text-sm font-medium">{{ currentDimensionLabel }}分布</div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{{ currentDimensionLabel }}</TableHead>
              <TableHead class="w-[110px]">成果数量</TableHead>
              <TableHead>占比</TableHead>
              <TableHead class="w-[90px] text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in tableRows" :key="row.name">
              <TableCell class="max-w-[160px] truncate font-medium">{{ row.name }}</TableCell>
              <TableCell>{{ row.value }}</TableCell>
              <TableCell>
                <div class="flex items-center gap-2">
                  <div class="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div class="h-full rounded-full bg-primary" :style="{ width: Math.min(row.percent, 100) + '%' }" />
                  </div>
                  <span class="w-12 text-right text-xs text-muted-foreground">{{ row.percent }}%</span>
                </div>
              </TableCell>
              <TableCell class="text-right">
                <Button variant="ghost" size="sm" @click="drillDown(row)">查看明细</Button>
              </TableCell>
            </TableRow>
            <TableEmpty v-if="!tableRows.length" :colspan="4">暂无统计数据</TableEmpty>
          </TableBody>
        </Table>
      </div>

      <div class="rounded-xl border bg-white p-4 shadow-sm">
        <div class="mb-3 text-sm font-medium">交叉分析：{{ rowLabel }} × {{ colLabel }}</div>
        <div class="mb-3 flex flex-wrap items-end gap-3">
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">行</Label>
            <Select v-model="crossRow" @update:model-value="loadCross">
              <SelectTrigger class="w-[130px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in crossDimensions" :key="item.value" :value="item.value">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">列</Label>
            <Select v-model="crossCol" @update:model-value="loadCross">
              <SelectTrigger class="w-[130px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in crossDimensions" :key="item.value" :value="item.value">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div class="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="min-w-[120px]">{{ rowLabel }}</TableHead>
                <TableHead v-for="col in crossCols" :key="col" class="w-[90px] text-center">{{ col }}</TableHead>
                <TableHead class="w-[80px] text-center">合计</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="row in crossRows" :key="row.name">
                <TableCell class="font-medium">{{ row.name }}</TableCell>
                <TableCell v-for="col in crossCols" :key="col" class="text-center">{{ row.cells[col] || 0 }}</TableCell>
                <TableCell class="text-center font-medium">{{ row.total }}</TableCell>
              </TableRow>
              <TableEmpty v-if="!crossRows.length" :colspan="crossCols.length + 2">暂无交叉数据</TableEmpty>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>

    <!-- 指标覆盖 + 排行 -->
    <div class="grid gap-4 lg:grid-cols-2">
      <div class="rounded-xl border bg-white shadow-sm">
        <div class="border-b px-4 py-3 text-sm font-medium">认证指标点覆盖情况</div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[70px]">编号</TableHead>
              <TableHead>指标点</TableHead>
              <TableHead class="w-[90px]">关联成果</TableHead>
              <TableHead>占比</TableHead>
              <TableHead class="w-[90px] text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in coverageItems" :key="row.id">
              <TableCell class="text-muted-foreground">{{ row.code }}</TableCell>
              <TableCell class="max-w-[130px] truncate font-medium">{{ row.name }}</TableCell>
              <TableCell>{{ row.value }}</TableCell>
              <TableCell>
                <div class="flex items-center gap-2">
                  <div class="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div class="h-full rounded-full bg-primary" :style="{ width: Math.min(row.percent, 100) + '%' }" />
                  </div>
                  <span class="w-12 text-right text-xs text-muted-foreground">{{ Math.min(row.percent, 100) }}%</span>
                </div>
              </TableCell>
              <TableCell class="text-right">
                <Button variant="ghost" size="sm" @click="drillIndicator(row)">查看明细</Button>
              </TableCell>
            </TableRow>
            <TableEmpty v-if="!coverageItems.length" :colspan="5">暂无指标点数据</TableEmpty>
          </TableBody>
        </Table>
      </div>

      <div class="rounded-xl border bg-white p-4 shadow-sm">
        <div class="mb-3 text-sm font-medium">个人成果排行</div>
        <div class="mb-3 inline-flex items-center gap-1 rounded-lg border bg-muted p-1">
          <Button :variant="rankingType === 'teacher' ? 'default' : 'ghost'" size="sm" @click="rankingType = 'teacher'; loadRanking()">教师</Button>
          <Button :variant="rankingType === 'student' ? 'default' : 'ghost'" size="sm" @click="rankingType = 'student'; loadRanking()">学生</Button>
          <Button :variant="rankingType === 'advisor' ? 'default' : 'ghost'" size="sm" @click="rankingType = 'advisor'; loadRanking()">指导学生</Button>
        </div>
        <EChart v-if="ranking.length" :option="rankingOption" :height="`${Math.max(ranking.length * 32 + 60, 220)}px`" />
        <div v-else class="py-12 text-center text-sm text-muted-foreground">暂无排行数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Award, BarChart3, Download, FileText, FolderOpen, RotateCcw, TrendingUp, TriangleAlert } from 'lucide-vue-next'
import EChart from '../components/EChart.vue'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ioApi, metaApi, statsApi } from '../api'
import { useUserStore } from '../stores/user'
import { saveBlob } from '../utils/file'

const router = useRouter()
const userStore = useUserStore()
const isElevated = computed(() => userStore.isElevated)

const dimensions = [
  { value: 'category', label: '按成果类型', axis: '成果类型' },
  { value: 'year', label: '按年度', axis: '年度' },
  { value: 'level', label: '按级别', axis: '成果级别' },
  { value: 'department', label: '按院系', axis: '院系' },
  { value: 'academic_year', label: '按学年', axis: '学年' },
  { value: 'status', label: '按审核状态', axis: '审核状态' },
  { value: 'owner_type', label: '按人员类型', axis: '人员类型' },
  { value: 'advisor', label: '按指导教师', axis: '指导教师' }
]

const crossDimensions = [
  { value: 'category', label: '成果类型' },
  { value: 'year', label: '年度' },
  { value: 'level', label: '级别' },
  { value: 'status', label: '审核状态' },
  { value: 'owner_type', label: '人员类型' }
]

const filters = reactive({
  year: '__all__',
  academic_year: '__all__',
  department: '__all__',
  owner_type: '__all__',
  status: 'approved'
})

const dimension = ref('category')
const items = ref([])
const counts = ref({})
const coverage = ref(null)
const loading = ref(false)
const exporting = ref(false)
const exportingMissing = ref(false)
const exportingPackage = ref(false)
const years = ref([])
const academicYears = ref([])
const departments = ref([])

const crossRow = ref('category')
const crossCol = ref('year')
const crossData = ref({ rows: [], cols: [], cells: {} })

const rankingType = ref('teacher')
const ranking = ref([])

const currentDimension = computed(() => dimensions.find((item) => item.value === dimension.value) || dimensions[0])
const currentDimensionLabel = computed(() => currentDimension.value.axis)
const total = computed(() => items.value.reduce((sum, item) => sum + item.value, 0))
const coverageItems = computed(() => (coverage.value && coverage.value.items) || [])

const rowLabel = computed(() => (crossDimensions.find((item) => item.value === crossRow.value) || {}).label || '')
const colLabel = computed(() => (crossDimensions.find((item) => item.value === crossCol.value) || {}).label || '')
const crossCols = computed(() => crossData.value.cols || [])
const crossRows = computed(() => {
  const cells = crossData.value.cells || {}
  return (crossData.value.rows || []).map((name) => {
    const rowCells = {}
    let sum = 0
    crossCols.value.forEach((col) => {
      const value = cells[`${name}||${col}`] || 0
      rowCells[col] = value
      sum += value
    })
    return { name, cells: rowCells, total: sum }
  })
})

const tableRows = computed(() => {
  const sum = total.value || 1
  return items.value.map((item) => ({
    ...item,
    percent: Math.round((item.value / sum) * 1000) / 10
  }))
})

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 24, top: 30, bottom: 70 },
  xAxis: {
    type: 'category',
    data: items.value.map((item) => item.name),
    axisLabel: { interval: 0, rotate: items.value.length > 6 ? 25 : 0 }
  },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      type: 'bar',
      barMaxWidth: 46,
      data: items.value.map((item) => item.value),
      label: { show: true, position: 'top' },
      itemStyle: { borderRadius: [8, 8, 0, 0], color: '#2f6feb' }
    }
  ]
}))

const rankingOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 90, right: 30, top: 20, bottom: 20 },
  xAxis: { type: 'value', minInterval: 1 },
  yAxis: {
    type: 'category',
    inverse: true,
    data: ranking.value.map((item) => item.name),
    axisLabel: { interval: 0, width: 80, overflow: 'truncate' }
  },
  series: [
    {
      type: 'bar',
      barMaxWidth: 18,
      data: ranking.value.map((item) => item.value),
      label: { show: true, position: 'right' },
      itemStyle: { color: '#00b2a9', borderRadius: [0, 6, 6, 0] }
    }
  ]
}))

function filterParams() {
  const params = {}
  Object.keys(filters).forEach((key) => {
    if (filters[key] && filters[key] !== '__all__') params[key] = filters[key]
  })
  return params
}

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

async function loadAll() {
  loading.value = true
  try {
    const params = filterParams()
    const [overview, breakdown, coverageData] = await Promise.all([
      statsApi.overview(params),
      statsApi.breakdown(dimension.value, params),
      statsApi.indicators(params)
    ])
    counts.value = overview.counts || {}
    items.value = breakdown.items || []
    coverage.value = coverageData
  } catch (err) {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function loadBreakdown() {
  loading.value = true
  try {
    const data = await statsApi.breakdown(dimension.value, filterParams())
    items.value = data.items || []
  } catch (err) {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function loadCross() {
  try {
    crossData.value = await statsApi.cross({
      row: crossRow.value,
      col: crossCol.value,
      ...filterParams()
    })
  } catch (err) {
    crossData.value = { rows: [], cols: [], cells: {} }
  }
}

async function loadRanking() {
  try {
    const params = { by: rankingType.value === 'student' ? 'student' : 'teacher', limit: 10 }
    if (rankingType.value === 'advisor') params.only_advisors = 1
    const data = await statsApi.ranking({ ...params, ...filterParams() })
    ranking.value = data.items || []
  } catch (err) {
    ranking.value = []
  }
}

function handleReset() {
  filters.year = '__all__'
  filters.academic_year = '__all__'
  filters.department = '__all__'
  filters.owner_type = '__all__'
  filters.status = 'approved'
  loadAll()
  loadCross()
  loadRanking()
}

function drillDown(row) {
  const query = { ...filterParams() }
  const key = dimension.value
  if (['category', 'year', 'level', 'academic_year', 'status', 'owner_type', 'department'].includes(key)) {
    query[key] = row.name
  }
  if (key === 'status') delete query.status
  router.push({ path: '/achievements', query })
}

function drillIndicator(row) {
  router.push({ path: '/achievements', query: { ...filterParams(), indicator_id: row.id } })
}

async function handleExport() {
  exporting.value = true
  try {
    const response = await ioApi.exportReport(filterParams())
    saveBlob(response, '专业业绩统计报表.xlsx')
  } catch (err) {
    // 统一错误处理
  } finally {
    exporting.value = false
  }
}

async function handleExportMissing() {
  exportingMissing.value = true
  try {
    const response = await ioApi.exportMissingEvidence({ ...filterParams(), has_attachment: '0' })
    saveBlob(response, '缺件清单.xlsx')
  } catch (err) {
    // 统一错误处理
  } finally {
    exportingMissing.value = false
  }
}

async function handleExportPackage() {
  exportingPackage.value = true
  try {
    const response = await ioApi.exportPackage(filterParams())
    saveBlob(response, '佐证材料包.zip')
  } catch (err) {
    // 统一错误处理
  } finally {
    exportingPackage.value = false
  }
}

onMounted(() => {
  loadMeta()
  loadAll()
  loadCross()
  loadRanking()
})
</script>