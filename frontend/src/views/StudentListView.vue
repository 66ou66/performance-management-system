<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">学生信息管理</h2>
        <p class="page-subtitle">
          学生基础信息与指导教师维护；学生账号仅能修改本人联系方式，学号/年级/专业等由管理员维护
        </p>
      </div>
      <el-button v-if="canManage" type="primary" :icon="Plus" @click="openCreate">新增学生</el-button>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="姓名/学号/邮箱"
            clearable
            style="width: 190px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="年级">
          <el-select
            v-model="filters.grade"
            placeholder="全部"
            clearable
            filterable
            allow-create
            style="width: 130px"
            @change="handleSearch"
          >
            <el-option v-for="item in grades" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="专业">
          <el-select
            v-model="filters.major"
            placeholder="全部"
            clearable
            filterable
            allow-create
            style="width: 170px"
            @change="handleSearch"
          >
            <el-option v-for="item in majors" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="指导教师">
          <el-select
            v-model="filters.advisor_id"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option
              v-for="item in teacherOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="账号">
          <el-select v-model="filters.has_account" placeholder="全部" clearable style="width: 120px" @change="handleSearch">
            <el-option label="已开通" value="1" />
            <el-option label="未开通" value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="items" v-loading="loading" border stripe empty-text="暂无学生数据">
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="grade" label="年级" width="90" />
        <el-table-column prop="major" label="专业" min-width="140" show-overflow-tooltip />
        <el-table-column prop="class_name" label="班级" width="110" />
        <el-table-column prop="advisor_names" label="指导教师" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.advisor_names">{{ row.advisor_names }}</span>
            <span v-else class="muted">未指定</span>
          </template>
        </el-table-column>
        <el-table-column label="账号" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.username" type="success" size="small" effect="plain">
              {{ row.username }}
            </el-tag>
            <span v-else class="muted">未开通</span>
          </template>
        </el-table-column>
        <el-table-column prop="achievement_count" label="成果数" width="90" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="viewAchievements(row)">成果</el-button>
            <template v-if="canManage">
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="isAdmin" link type="danger" size="small" @click="handleDelete(row)">
                删除
              </el-button>
            </template>
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

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增学生' : '编辑学生'"
      width="620px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="学号" prop="student_no">
              <el-input v-model="form.student_no" maxlength="50" placeholder="请输入学号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="form.name" maxlength="80" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="年级">
              <el-select
                v-model="form.grade"
                placeholder="请选择或输入"
                clearable
                filterable
                allow-create
                style="width: 100%"
              >
                <el-option v-for="item in grades" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="班级">
              <el-input v-model="form.class_name" maxlength="80" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="专业">
              <el-select
                v-model="form.major"
                placeholder="请选择或输入"
                clearable
                filterable
                allow-create
                style="width: 100%"
              >
                <el-option v-for="item in majors" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属院系">
              <el-select
                v-model="form.department"
                placeholder="请选择或输入"
                clearable
                filterable
                allow-create
                style="width: 100%"
              >
                <el-option v-for="item in departments" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="form.email" maxlength="120" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.phone" maxlength="30" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">指导教师（第一位为主导师）</el-divider>
        <el-form-item label="指导教师">
          <el-select
            v-model="form.advisor_ids"
            multiple
            filterable
            placeholder="可选择多位指导教师"
            style="width: 100%"
          >
            <el-option
              v-for="item in teacherOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <template v-if="dialogMode === 'create'">
          <el-divider content-position="left">登录账号（可选）</el-divider>
          <el-form-item label="登录名" prop="username">
            <el-input v-model="form.username" maxlength="80" placeholder="留空则不创建账号" />
          </el-form-item>
          <el-form-item label="初始密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              :placeholder="`长度不少于 ${minPasswordLength} 位`"
            />
          </el-form-item>
          <el-form-item label="首次改密">
            <el-switch v-model="form.must_change_password" />
            <span class="muted" style="margin-left: 8px">开启后该账号首次登录需修改密码</span>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="学生档案" size="640px">
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="学号">{{ detail.student_no }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ detail.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ detail.class_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="专业">{{ detail.major || '-' }}</el-descriptions-item>
          <el-descriptions-item label="所属院系">{{ detail.department || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ detail.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ detail.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="登录账号">{{ detail.username || '未开通' }}</el-descriptions-item>
          <el-descriptions-item label="指导教师">
            {{ detail.advisor_names || '未指定' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="chart-title" style="margin-top: 16px">
          业绩成果（{{ (detail.achievements || []).length }} 条）
        </div>
        <el-table :data="detail.achievements || []" border size="small" empty-text="暂无成果">
          <el-table-column prop="title" label="成果名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="category" label="类型" width="110" />
          <el-table-column prop="level" label="级别" width="90" />
          <el-table-column prop="year" label="年份" width="80" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTagTypes[row.status] || 'info'">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, RefreshLeft, Search } from '@element-plus/icons-vue'
import { metaApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'
import { statusLabel, statusTagTypes } from '../utils/file'

const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const canManage = computed(() => userStore.isAdmin || userStore.role === 'reviewer')
const minPasswordLength = computed(
  () => (userStore.hints && userStore.hints.min_password_length) || 6
)

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const saving = ref(false)
const grades = ref([])
const majors = ref([])
const departments = ref([])
const teacherOptions = ref([])

const filters = reactive({
  keyword: '',
  grade: '',
  major: '',
  advisor_id: '',
  has_account: ''
})

const dialogVisible = ref(false)
const dialogMode = ref('create')
const formRef = ref(null)
const detailVisible = ref(false)
const detail = ref(null)

function emptyForm() {
  return {
    id: null,
    student_no: '',
    name: '',
    grade: '',
    major: '',
    department: '',
    class_name: '',
    email: '',
    phone: '',
    advisor_ids: [],
    username: '',
    password: '',
    must_change_password: false
  }
}

const form = reactive(emptyForm())

const formRules = {
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入学生姓名', trigger: 'blur' }],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!form.username) {
          callback()
          return
        }
        if (!value || value.length < minPasswordLength.value) {
          callback(new Error(`初始密码长度不能少于 ${minPasswordLength.value} 位`))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

async function loadMeta() {
  try {
    const data = await metaApi.options()
    grades.value = data.grades || []
    majors.value = data.majors || []
    departments.value = data.departments || []
  } catch (err) {
    // 统一错误处理
  }
  try {
    teacherOptions.value = await teacherApi.options()
  } catch (err) {
    teacherOptions.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.keys(filters).forEach((key) => {
      if (filters[key] !== '') params[key] = filters[key]
    })
    const data = await studentApi.list(params)
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
  page.value = 1
  loadList()
}

function handleSizeChange() {
  page.value = 1
  loadList()
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    ...emptyForm(),
    id: row.id,
    student_no: row.student_no,
    name: row.name,
    grade: row.grade || '',
    major: row.major || '',
    department: row.department || '',
    class_name: row.class_name || '',
    email: row.email || '',
    phone: row.phone || '',
    advisor_ids: (row.advisors || []).map((item) => item.teacher_id)
  })
  dialogVisible.value = true
}

async function openDetail(row) {
  detail.value = row
  detailVisible.value = true
  try {
    const data = await studentApi.profile(row.id)
    detail.value = { ...row, ...data }
  } catch (err) {
    // 保持已有基本信息
  }
}

function viewAchievements(row) {
  router.push({ path: '/achievements', query: { owner_name: row.name, owner_type: 'student' } })
}

function resetForm() {
  if (formRef.value) formRef.value.clearValidate()
  Object.assign(form, emptyForm())
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      student_no: form.student_no.trim(),
      name: form.name.trim(),
      grade: form.grade,
      major: form.major,
      department: form.department,
      class_name: form.class_name,
      email: form.email,
      phone: form.phone,
      advisor_ids: form.advisor_ids
    }
    if (dialogMode.value === 'create') {
      if (form.username.trim()) {
        payload.username = form.username.trim()
        payload.password = form.password
        payload.must_change_password = form.must_change_password
      }
      await studentApi.create(payload)
      ElMessage.success('学生新增成功')
    } else {
      await studentApi.update(form.id, payload)
      ElMessage.success('学生信息已更新')
    }
    dialogVisible.value = false
    await loadList()
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

function handleDelete(row) {
  ElMessageBox.confirm(
    `确认删除学生「${row.name}」吗？其 ${row.achievement_count} 条成果、支撑材料、指导关系以及登录账号将一并删除，且不可恢复。`,
    '删除确认',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'error' }
  )
    .then(async () => {
      await studentApi.remove(row.id)
      ElMessage.success('学生已删除')
      if (items.value.length === 1 && page.value > 1) page.value -= 1
      loadList()
    })
    .catch(() => {})
}

onMounted(() => {
  loadMeta()
  loadList()
})
</script>

<style scoped>
.muted {
  color: #909399;
  font-size: 12px;
}
</style>