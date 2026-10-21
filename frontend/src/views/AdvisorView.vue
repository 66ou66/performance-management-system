<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ isTeacher ? '我的指导学生' : '指导关系管理' }}</h2>
        <p class="page-subtitle">
          建立教师与学生之间的指导关系后，教师的教学业绩可与学生的竞赛、论文等成果自动关联
        </p>
      </div>
      <el-button v-if="isAdmin" type="primary" :icon="Plus" @click="openCreate">
        新增指导关系
      </el-button>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item v-if="!isTeacher" label="指导教师">
          <el-select
            v-model="teacherId"
            placeholder="全部"
            clearable
            filterable
            style="width: 200px"
            @change="handleSearch"
          >
            <el-option
              v-for="item in teachers"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="学生">
          <el-select
            v-model="studentId"
            placeholder="全部"
            clearable
            filterable
            style="width: 200px"
            @change="handleSearch"
          >
            <el-option
              v-for="item in students"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" @click="loadList">刷新</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="items" v-loading="loading" border stripe empty-text="暂无指导关系">
        <el-table-column prop="teacher_name" label="指导教师" width="150" />
        <el-table-column prop="student_name" label="学生" width="150" />
        <el-table-column label="主导师" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_primary" size="small" type="success">主导师</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_year" label="起始年份" width="100" />
        <el-table-column prop="end_year" label="结束年份" width="100" />
        <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="指导成果" width="110">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="viewAchievements(row)">
              查看成果
            </el-link>
          </template>
        </el-table-column>
        <el-table-column v-if="isAdmin" label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="togglePrimary(row)">
              {{ row.is_primary ? '取消主导师' : '设为主导师' }}
            </el-button>
            <el-button link type="danger" size="small" @click="remove(row)">解除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadList"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新增指导关系" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="指导教师" prop="teacher_id">
          <el-select v-model="form.teacher_id" filterable placeholder="请选择" style="width: 100%">
            <el-option v-for="item in teachers" :key="item.id" :label="item.label" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生" prop="student_id">
          <el-select v-model="form.student_id" filterable placeholder="请选择" style="width: 100%">
            <el-option v-for="item in students" :key="item.id" :label="item.label" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="主导师">
          <el-switch v-model="form.is_primary" />
        </el-form-item>
        <el-form-item label="起始年份">
          <el-input-number v-model="form.start_year" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" maxlength="200" show-word-limit />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { advisorApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const router = useRouter()
const isAdmin = computed(() => userStore.role === 'admin')
const isTeacher = computed(() => userStore.role === 'teacher')

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const teacherId = ref(null)
const studentId = ref(null)
const teachers = ref([])
const students = ref([])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const form = reactive({ teacher_id: null, student_id: null, is_primary: false, start_year: null, note: '' })
const rules = {
  teacher_id: [{ required: true, message: '请选择指导教师', trigger: 'change' }],
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }]
}

async function loadOptions() {
  try {
    if (!isTeacher.value || isAdmin.value) {
      teachers.value = await teacherApi.options()
    } else if (userStore.user) {
      teachers.value = [{
        id: userStore.user.owner_id,
        label: `${userStore.displayName}（本人）`
      }]
    }
  } catch (err) {
    teachers.value = []
  }
  try {
    students.value = await studentApi.options()
  } catch (err) {
    // 教师账号没有学生名册权限时，仍可通过已建立的指导关系查看
    const list = await advisorApi.list({ page: 1, page_size: 100 }).catch(() => ({ items: [] }))
    const seen = new Map()
    ;(list.items || []).forEach((row) => {
      if (row.student_id && !seen.has(row.student_id)) {
        seen.set(row.student_id, { id: row.student_id, label: row.student_name })
      }
    })
    students.value = Array.from(seen.values())
  }
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (teacherId.value) params.teacher_id = teacherId.value
    if (studentId.value) params.student_id = studentId.value
    const data = await advisorApi.list(params)
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

function handleSizeChange() {
  page.value = 1
  loadList()
}

function openCreate() {
  Object.assign(form, {
    teacher_id: teacherId.value || null,
    student_id: studentId.value || null,
    is_primary: false,
    start_year: new Date().getFullYear(),
    note: ''
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await advisorApi.create({ ...form })
    ElMessage.success('指导关系已新增')
    dialogVisible.value = false
    loadList()
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

async function togglePrimary(row) {
  try {
    await advisorApi.update(row.id, { is_primary: !row.is_primary })
    ElMessage.success('已更新')
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function remove(row) {
  ElMessageBox.confirm(
    `确认解除「${row.teacher_name}」与「${row.student_name}」的指导关系吗？`,
    '解除确认',
    { confirmButtonText: '解除', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await advisorApi.remove(row.id)
      ElMessage.success('已解除')
      loadList()
    })
    .catch(() => {})
}

function viewAchievements(row) {
  router.push({
    path: '/achievements',
    query: { owner_name: row.student_name }
  })
}

onMounted(async () => {
  await loadOptions()
  loadList()
})
</script>

<style scoped>
.muted {
  color: #909399;
}
</style>