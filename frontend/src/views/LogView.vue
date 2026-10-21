<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">操作日志审计</h2>
        <p class="page-subtitle">
          记录登录、录入、修改、删除、审核、导入导出等关键操作，用于认证材料的可追溯性核查
        </p>
      </div>
      <el-button :icon="Refresh" @click="loadList">刷新</el-button>
    </div>

    <div class="card">
      <div ref="chartRef" class="chart"></div>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" placeholder="全部" clearable style="width: 150px">
            <el-option
              v-for="item in actions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="对象">
          <el-select v-model="filters.target_type" placeholder="全部" clearable style="width: 130px">
            <el-option
              v-for="item in targets"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="filters.username" placeholder="登录名" clearable style="width: 130px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="描述内容"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="items" v-loading="loading" border stripe empty-text="暂无日志">
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column prop="username" label="操作人" width="120">
          <template #default="{ row }">{{ row.username || '系统' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="对象" width="100">
          <template #default="{ row }">{{ targetLabel(row.target_type) }}</template>
        </el-table-column>
        <el-table-column prop="summary" label="描述" min-width="280" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="详情" width="90">
          <template #default="{ row }">
            <el-button v-if="row.detail" link type="primary" size="small" @click="openDetail(row)">
              查看
            </el-button>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadList"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="操作详情" width="560px">
      <pre class="detail-json">{{ detailText }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh, RefreshLeft, Search } from '@element-plus/icons-vue'
import { logApi } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const actions = ref([])
const targets = ref([])
const dateRange = ref([])
const detailVisible = ref(false)
const detailRow = ref(null)
const chartRef = ref(null)
let chart = null

const filters = reactive({ action: '', target_type: '', username: '', keyword: '' })

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
      if (filters[key]) params[key] = filters[key]
    })
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const data = await logApi.list(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  Object.keys(filters).forEach((key) => {
    filters[key] = ''
  })
  dateRange.value = []
  page.value = 1
  loadList()
}

function handleSizeChange() {
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

<style scoped>
.chart {
  height: 220px;
}

.detail-json {
  max-height: 420px;
  overflow: auto;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  margin: 0;
}

.muted {
  color: #909399;
}
</style>