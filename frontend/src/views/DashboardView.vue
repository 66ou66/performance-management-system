<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">数据看板</h2>
        <p class="page-subtitle">
          {{ isElevated ? '专业师生业绩数据的整体概览，可直接下钻到明细' : '我的业绩成果汇总概览' }}
        </p>
      </div>
      <div class="page-actions">
        <el-select v-model="filterYear" placeholder="全部年份" clearable style="width: 120px" @change="loadData">
          <el-option v-for="item in years" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select
          v-model="filterAcademicYear"
          placeholder="全部学年"
          clearable
          style="width: 130px"
          @change="loadData"
        >
          <el-option v-for="item in academicYears" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select
          v-if="isElevated"
          v-model="filterDepartment"
          placeholder="全部院系"
          clearable
          filterable
          style="width: 140px"
          @change="loadData"
        >
          <el-option v-for="item in departments" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新数据</el-button>
      </div>
    </div>

    <div class="stat-grid" v-loading="loading">
      <div
        v-for="card in cards"
        :key="card.label"
        class="stat-card clickable"
        @click="drillDown(card)"
      >
        <div class="stat-icon" :style="{ background: card.color }">
          <el-icon><component :is="card.icon" /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <div class="chart-grid">
      <div class="chart-card">
        <div class="chart-title">成果类型分布</div>
        <EChart v-if="byCategory.length" :option="pieOption" height="300px" />
        <el-empty v-else description="暂无数据" :image-size="70" />
      </div>
      <div class="chart-card">
        <div class="chart-title">年度成果趋势（含同比）</div>
        <EChart v-if="trend.length" :option="lineOption" height="300px" />
        <el-empty v-else description="暂无数据" :image-size="70" />
      </div>
      <div class="chart-card">
        <div class="chart-title">成果级别分布</div>
        <EChart v-if="byLevel.length" :option="levelOption" height="300px" />
        <el-empty v-else description="暂无数据" :image-size="70" />
      </div>
      <div class="chart-card">
        <div class="chart-title">院系成果分布</div>
        <EChart v-if="byDepartment.length" :option="departmentOption" height="300px" />
        <el-empty v-else description="暂无数据" :image-size="70" />
      </div>
    </div>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col v-if="isElevated" :span="12">
        <div class="card">
          <div class="chart-title">教师成果排行 TOP10</div>
          <el-table :data="teacherRanking" size="small" empty-text="暂无数据" @row-click="rankingClick">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="name" label="教师" min-width="120" />
            <el-table-column prop="value" label="成果数" width="90" />
          </el-table>
        </div>
      </el-col>
      <el-col v-if="isElevated" :span="12">
        <div class="card">
          <div class="chart-title">学生成果排行 TOP10</div>
          <el-table :data="studentRanking" size="small" empty-text="暂无数据" @row-click="rankingClick">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="name" label="学生" min-width="120" />
            <el-table-column prop="value" label="成果数" width="90" />
          </el-table>
        </div>
      </el-col>
      <el-col :span="isElevated ? 24 : 12">
        <div class="card" style="margin-top: 16px">
          <div class="table-toolbar">
            <span class="chart-title" style="margin: 0">最近业绩成果</span>
            <el-button text type="primary" @click="router.push('/achievements')">查看全部</el-button>
          </div>
          <el-table :data="recent" v-loading="loading" empty-text="暂无成果数据">
            <el-table-column prop="title" label="成果名称" min-width="260" show-overflow-tooltip />
            <el-table-column label="所属人" width="150">
              <template #default="{ row }">
                {{ row.owner_name }}
                <el-tag size="small" type="info" effect="plain">
                  {{ ownerTypeLabel(row.owner_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="成果类型" width="130" />
            <el-table-column prop="level" label="级别" width="100" />
            <el-table-column prop="year" label="年份" width="90" />
            <el-table-column label="材料" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.attachment_count" size="small" type="success" effect="plain">
                  已归档
                </el-tag>
                <el-tag v-else size="small" type="danger" effect="plain">缺材料</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="录入时间" width="170" />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Avatar,
  Files,
  Medal,
  Refresh,
  TrendCharts,
  UserFilled,
  WarningFilled
} from '@element-plus/icons-vue'
import EChart from '../components/EChart.vue'
import { achievementApi, metaApi, statsApi } from '../api'
import { useUserStore } from '../stores/user'
import { ownerTypeLabel } from '../utils/file'

const router = useRouter()
const userStore = useUserStore()
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

const filterYear = ref('')
const filterAcademicYear = ref('')
const filterDepartment = ref('')
const years = ref([])
const academicYears = ref([])
const departments = ref([])

const filterParams = computed(() => {
  const params = {}
  if (filterYear.value) params.year = filterYear.value
  if (filterAcademicYear.value) params.academic_year = filterAcademicYear.value
  if (filterDepartment.value) params.department = filterDepartment.value
  return params
})

const cards = computed(() => {
  const list = []
  if (isElevated.value) {
    list.push(
      { label: '教师总数', value: counts.value.teachers || 0, icon: UserFilled, color: '#2f6feb', path: '/teachers' },
      { label: '学生总数', value: counts.value.students || 0, icon: Avatar, color: '#13c2c2', path: '/students' }
    )
  }
  list.push(
    {
      label: '成果总数',
      value: counts.value.achievements || 0,
      icon: Medal,
      color: '#6f4cf0',
      query: { ...filterParams.value }
    },
    {
      label: '本年度成果',
      value: counts.value.this_year || 0,
      icon: TrendCharts,
      color: '#e6a23c',
      query: { ...filterParams.value }
    },
    {
      label: '已归档材料成果',
      value: counts.value.attachments || 0,
      icon: Files,
      color: '#67c23a',
      query: { ...filterParams.value, has_attachment: '1' }
    },
    {
      label: '缺失材料成果',
      value: counts.value.missing_evidence || 0,
      icon: WarningFilled,
      color: '#f56c6c',
      query: { ...filterParams.value, has_attachment: '0' }
    }
  )
  if (isElevated.value) {
    list.push({
      label: '待审核成果',
      value: counts.value.pending || 0,
      icon: Files,
      color: '#909399',
      path: '/reviews'
    })
  }
  return list
})

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} 项 ({d}%)' },
  legend: { type: 'scroll', bottom: 0 },
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
      const change = row.change_percent === null || row.change_percent === undefined
        ? '—'
        : `${row.change_percent}%`
      return `${item.name} 年<br/>成果数：${item.value}<br/>同比：${change}`
    }
  },
  grid: { left: 40, right: 20, top: 30, bottom: 40 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: trend.value.map((item) => item.name)
  },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.18 },
      symbolSize: 8,
      data: trend.value.map((item) => item.value),
      itemStyle: { color: '#2f6feb' }
    }
  ]
}))

const levelOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 50 },
  xAxis: {
    type: 'category',
    data: byLevel.value.map((item) => item.name),
    axisLabel: { interval: 0, rotate: 20 }
  },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      type: 'bar',
      barMaxWidth: 38,
      data: byLevel.value.map((item) => item.value),
      itemStyle: { color: '#67c23a', borderRadius: [6, 6, 0, 0] }
    }
  ]
}))

const departmentOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 60 },
  xAxis: {
    type: 'category',
    data: byDepartment.value.map((item) => item.name),
    axisLabel: { interval: 0, rotate: 25 }
  },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      type: 'bar',
      barMaxWidth: 38,
      data: byDepartment.value.map((item) => item.value),
      itemStyle: { color: '#6f4cf0', borderRadius: [6, 6, 0, 0] }
    }
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
  router.push({
    path: '/achievements',
    query: { owner_name: row.name, ...filterParams.value }
  })
}

onMounted(() => {
  loadMeta()
  loadData()
})
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.clickable {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.clickable:hover {
  box-shadow: 0 4px 16px rgba(31, 45, 61, 0.12);
}
</style>