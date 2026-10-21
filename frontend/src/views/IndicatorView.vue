<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">认证指标点管理</h2>
        <p class="page-subtitle">
          工程教育认证毕业要求指标点：用于把教师与学生的业绩成果挂接到具体毕业要求，形成达成度支撑
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="loadAll">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增指标点</el-button>
      </div>
    </div>

    <div class="card">
      <el-alert
        v-if="coverage"
        type="info"
        :closable="false"
        show-icon
        class="coverage-alert"
      >
        <template #title>
          当前统计口径下共 {{ coverage.total_achievements }} 条成果，
          其中 {{ coverage.covered_achievements }} 条已关联指标点（覆盖率
          {{ coverage.coverage_percent }}%）；未覆盖指标点：
          {{ coverage.uncovered_indicators.length ? coverage.uncovered_indicators.join('、') : '无' }}
        </template>
      </el-alert>

      <el-table :data="items" v-loading="loading" border stripe empty-text="暂无指标点">
        <el-table-column prop="code" label="编号" width="80" />
        <el-table-column prop="name" label="指标点名称" width="200" />
        <el-table-column prop="description" label="说明" min-width="300" show-overflow-tooltip />
        <el-table-column prop="achievement_count" label="关联成果" width="110">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="viewAchievements(row)">
              {{ row.achievement_count || 0 }} 条
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑指标点' : '新增指标点'"
      width="560px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="编号" prop="code">
          <el-input v-model="form.code" placeholder="例如 1 或 3.2" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="例如 工程知识" maxlength="120" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { indicatorApi, statsApi } from '../api'

const router = useRouter()
const items = ref([])
const coverage = ref(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, code: '', name: '', description: '', sort_order: 0, is_active: true })
const rules = {
  code: [{ required: true, message: '请输入指标点编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入指标点名称', trigger: 'blur' }]
}

async function loadAll() {
  loading.value = true
  try {
    const data = await indicatorApi.list({ page: 1, page_size: 100, include_inactive: 1 })
    items.value = data.items || []
    coverage.value = await statsApi.indicators()
  } catch (err) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, {
    id: null,
    code: '',
    name: '',
    description: '',
    sort_order: (items.value.length || 0) + 1,
    is_active: true
  })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    code: row.code,
    name: row.name,
    description: row.description || '',
    sort_order: row.sort_order || 0,
    is_active: row.is_active !== false
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description,
      sort_order: form.sort_order,
      is_active: form.is_active
    }
    if (form.id) {
      await indicatorApi.update(form.id, payload)
      ElMessage.success('指标点已更新')
    } else {
      await indicatorApi.create(payload)
      ElMessage.success('指标点已新增')
    }
    dialogVisible.value = false
    loadAll()
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

function remove(row) {
  ElMessageBox.confirm(
    `删除指标点「${row.code} ${row.name}」将解除 ${row.achievement_count || 0} 条成果的关联，确认继续吗？`,
    '删除确认',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await indicatorApi.remove(row.id)
      ElMessage.success('指标点已删除')
      loadAll()
    })
    .catch(() => {})
}

function viewAchievements(row) {
  router.push({ path: '/achievements', query: { indicator_id: row.id } })
}

onMounted(loadAll)
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
}

.coverage-alert {
  margin-bottom: 12px;
}
</style>