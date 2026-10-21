<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">统计报表</h2>
        <p class="page-subtitle">
          按成果类型、年度、级别、院系、学年、状态多维度统计，支持交叉分析与认证指标点覆盖率
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Files" :loading="exportingMissing" @click="handleExportMissing">
          导出缺件清单
        </el-button>
        <el-button :icon="FolderOpened" :loading="exportingPackage" @click="handleExportPackage">
          导出佐证材料包
        </el-button>
        <el-button
          v-if="isElevated"
          type="primary"
          :icon="Download"
          :loading="exporting"
          @click="handleExport"
        >
          导出统计报表
        </el-button>
      </div>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="年份">
          <el-select v-model="filters.year" placeholder="全部" clearable style="width: 110px" @change="loadAll">
            <el-option v-for="item in years" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="学年">
          <el-select
            v-model="filters.academic_year"
            placeholder="全部"
            clearable
            style="width: 130px"
            @change="loadAll"
          >
            <el-option v-for="item in academicYears" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="院系">
          <el-select
            v-model="filters.department"
            placeholder="全部"
            clearable
            filterable
            style="width: 150px"
            @change="loadAll"
          >
            <el-option v-for="item in departments" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isElevated" label="人员类型">
          <el-select v-model="filters.owner_type" placeholder="全部" clearable style="width: 110px" @change="loadAll">
            <el-option label="教师" value="teacher" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isElevated" label="统计口径">
          <el-select v-model="filters.status" style="width: 130px" @change="loadAll">
            <el-option label="仅已通过" value="approved" />
            <el-option label="待审核" value="pending" />
            <el-option label="草稿" value="draft" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="stat-grid" v-loading="loading">
      <div class="stat-card">
        <div class="stat-icon" style="background: #6f4cf0"><el-icon><Medal /></el-icon></div>
        <div>
          <div class="stat-value">{{ counts.achievements || 0 }}</div>
          <div class="stat-label">成果总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #67c23a"><el-icon><Files /></el-icon></div>
        <div>
          <div class="stat-value">{{ counts.attachments || 0 }}</div>
          <div class="stat-label">已归档材料</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f56c6c"><el-icon><WarningFilled /></el-icon></div>
        <div>
          <div class="stat-value">{{ counts.missing_evidence || 0 }}</div>
          <div class="stat-label">缺少材料</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e6a23c"><el-icon><TrendCharts /></el-icon></div>
        <div>
          <div class="stat-value">{{ counts.this_year || 0 }}</div>
          <div class="stat-label">本年度成果</div>
        </div>
      </div>
      <div v-if="coverage" class="stat-card">
        <div class="stat-icon" style="background: #2f6feb"><el-icon><DataAnalysis /></el-icon></div>
        <div>
          <div class="stat-value">{{ coverage.coverage_percent }}%</div>
          <div class="stat-label">指标点覆盖率</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="table-toolbar">
        <el-radio-group v-model="dimension" @change="loadBreakdown">
          <el-radio-button v-for="item in dimensions" :key="item.value" :value="item.value">
            {{ item.label }}
          </el-radio-button>
        </el-radio-group>
        <span class="muted">统计维度：{{ currentDimensionLabel }}，共 {{ total }} 条</span>
      </div>

      <div v-loading="loading">
        <EChart v-if="items.length" :option="chartOption" height="360px" />
        <el-empty v-else description="暂无统计数据" :image-size="80" />
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <div class="card">
          <el-table :data="tableRows" border stripe empty-text="暂无统计数据">
            <el-table-column prop="name" :label="currentDimensionLabel" min-width="160" />
            <el-table-column prop="value" label="成果数量" width="110" sortable />
            <el-table-column label="占比" min-width="180">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.percent"
                  :stroke-width="12"
                  :format="() => `${row.percent}%`"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="drillDown(row)">查看明细</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div class="chart-title">交叉分析：{{ rowLabel }} × {{ colLabel }}</div>
          <el-form :inline="true" size="small" style="margin-bottom: 8px">
            <el-form-item label="行">
              <el-select v-model="crossRow" style="width: 130px" @change="loadCross">
                <el-option
                  v-for="item in crossDimensions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="列">
              <el-select v-model="crossCol" style="width: 130px" @change="loadCross">
                <el-option
                  v-for="item in crossDimensions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-form>
          <el-table :data="crossRows" border size="small" empty-text="暂无交叉数据">
            <el-table-column prop="name" :label="rowLabel" width="120" fixed />
            <el-table-column
              v-for="col in crossCols"
              :key="col"
              :label="col"
              width="90"
              align="center"
            >
              <template #default="{ row }">{{ row.cells[col] || 0 }}</template>
            </el-table-column>
            <el-table-column prop="total" label="合计" width="80" align="center" fixed="right" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <div class="card">
          <div class="chart-title">认证指标点覆盖情况</div>
          <el-table :data="coverageItems" border size="small" empty-text="暂无指标点数据">
            <el-table-column prop="code" label="编号" width="70" />
            <el-table-column prop="name" label="指标点" min-width="130" />
            <el-table-column prop="value" label="关联成果" width="90" sortable />
            <el-table-column label="占比" min-width="160">
              <template #default="{ row }">
                <el-progress :percentage="Math.min(row.percent, 100)" :stroke-width="10" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="drillIndicator(row)">
                  查看明细
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <div class="chart-title">个人成果排行</div>
          <el-radio-group v-model="rankingType" size="small" style="margin-bottom: 8px" @change="loadRanking">
            <el-radio-button value="teacher">教师</el-radio-button>
            <el-radio-button value="student">学生</el-radio-button>
            <el-radio-button value="advisor">指导学生</el-radio-button>
          </el-radio-group>
          <EChart v-if="ranking.length" :option="rankingOption" :height="`${Math.max(ranking.length * 32 + 60, 220)}px`" />
          <el-empty v-else description="暂无排行数据" :image-size="70" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  DataAnalysis,
  Download,
  Files,
  FolderOpened,
  Medal,
  RefreshLeft,
  TrendCharts,
  WarningFilled
} from '@element-plus/icons-vue'
import EChart from '../components/EChart.vue'
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
  year: '',
  academic_year: '',
  department: '',
  owner_type: '',
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

const currentDimension = computed(
  () => dimensions.find((item) => item.value === dimension.value) || dimensions[0]
)
const currentDimensionLabel = computed(() => currentDimension.value.axis)
const total = computed(() => items.value.reduce((sum, item) => sum + item.value, 0))
const coverageItems = computed(() => (coverage.value && coverage.value.items) || [])

const rowLabel = computed(
  () => (crossDimensions.find((item) => item.value === crossRow.value) || {}).label || ''
)
const colLabel = computed(
  () => (crossDimensions.find((item) => item.value === crossCol.value) || {}).label || ''
)
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
      itemStyle: { color: '#67c23a', borderRadius: [0, 6, 6, 0] }
    }
  ]
}))

function filterParams() {
  const params = {}
  Object.keys(filters).forEach((key) => {
    if (filters[key]) params[key] = filters[key]
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
  filters.year = ''
  filters.academic_year = ''
  filters.department = ''
  filters.owner_type = ''
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

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
}

.muted {
  color: #909399;
  font-size: 13px;
}
</style>