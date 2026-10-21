<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">账号权限管理</h2>
        <p class="page-subtitle">
          管理登录账号、角色权限（管理员 / 审核员 / 教师 / 学生）、启用状态与密码重置
        </p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增账号</el-button>
    </div>

    <div class="card">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="权限说明：管理员拥有全部权限；审核员可审核成果、查看全部档案但不能删除人员；教师仅能维护本人成果（含「指导学生成果」类别）；学生仅能维护本人成果。"
        style="margin-bottom: 12px"
      />

      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="登录名/人员姓名"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="管理员" value="admin" />
            <el-option label="审核员" value="reviewer" />
            <el-option label="教师" value="teacher" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px" @change="handleSearch">
            <el-option label="启用" value="1" />
            <el-option label="禁用" value="0" />
          </el-select>
        </el-form-item>
        <el-form-item label="人员绑定">
          <el-select v-model="filters.linked" placeholder="全部" clearable style="width: 130px" @change="handleSearch">
            <el-option label="已绑定" value="1" />
            <el-option label="未绑定" value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="items" v-loading="loading" border stripe empty-text="暂无账号数据">
        <el-table-column prop="username" label="登录名" min-width="130" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagTypes[row.role] || 'info'" size="small">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联人员" min-width="150">
          <template #default="{ row }">
            <template v-if="row.owner_name">
              {{ row.owner_name }}
              <el-tag size="small" effect="plain" type="info">
                {{ ownerTypeLabel(row.owner_type) }}
              </el-tag>
            </template>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="密码状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.must_change_password" size="small" type="warning">待修改</el-tag>
            <span v-else class="muted">已设置</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              :disabled="row.id === (userStore.user && userStore.user.id)"
              active-text="启用"
              inactive-text="禁用"
              inline-prompt
              @change="(value) => handleStatusChange(row, value)"
            />
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="165">
          <template #default="{ row }">{{ row.last_login_at || '从未登录' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="165" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="handleResetPassword(row)">
              重置密码
            </el-button>
            <el-button
              v-if="row.owner_type"
              link
              type="primary"
              size="small"
              @click="handleUnbind(row)"
            >
              解绑
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.id === (userStore.user && userStore.user.id)"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
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
      :title="dialogMode === 'create' ? '新增账号' : '编辑账号角色'"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="登录名" prop="username">
          <el-input
            v-model="form.username"
            maxlength="80"
            :disabled="dialogMode === 'edit'"
            placeholder="请输入登录名"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role" @change="handleRoleChange">
            <el-radio-button value="admin">管理员</el-radio-button>
            <el-radio-button value="reviewer">审核员</el-radio-button>
            <el-radio-button value="teacher">教师</el-radio-button>
            <el-radio-button value="student">学生</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item
          v-if="form.role === 'teacher' || form.role === 'student'"
          label="关联人员"
          prop="owner_id"
        >
          <el-select v-model="form.owner_id" filterable placeholder="请选择关联人员" style="width: 100%">
            <el-option v-for="item in ownerOptions" :key="item.id" :label="item.label" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-alert
          v-else
          type="info"
          :closable="false"
          show-icon
          :title="form.role === 'reviewer'
            ? '审核员不绑定具体人员档案，可查看全部档案并审核成果。'
            : '管理员账号拥有全部权限，请谨慎分配。'"
          style="margin-bottom: 12px"
        />
        <template v-if="dialogMode === 'create'">
          <el-form-item label="登录密码" prop="password">
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, RefreshLeft, Search } from '@element-plus/icons-vue'
import { studentApi, teacherApi, userApi } from '../api'
import { useUserStore } from '../stores/user'
import { ownerTypeLabel, roleLabel, roleTagTypes } from '../utils/file'

const userStore = useUserStore()
const minPasswordLength = computed(
  () => (userStore.hints && userStore.hints.min_password_length) || 6
)

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const saving = ref(false)

const filters = reactive({ keyword: '', role: '', status: '', linked: '' })

const dialogVisible = ref(false)
const dialogMode = ref('create')
const formRef = ref(null)
const ownerOptions = ref([])

function emptyForm() {
  return {
    id: null,
    username: '',
    role: 'teacher',
    owner_id: null,
    password: '',
    must_change_password: false
  }
}

const form = reactive(emptyForm())

const formRules = {
  username: [{ required: true, message: '请输入登录名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  owner_id: [{ required: true, message: '请选择关联人员', trigger: 'change' }],
  password: [
    { required: true, message: '请输入登录密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ]
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.keys(filters).forEach((key) => {
      if (filters[key] !== '') params[key] = filters[key]
    })
    const data = await userApi.list(params)
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

async function loadOwnerOptions(role, mode) {
  ownerOptions.value = []
  if (role !== 'teacher' && role !== 'student') return
  try {
    if (mode === 'create') {
      const list = await userApi.candidates(role)
      ownerOptions.value = list.map((item) => ({ id: item.id, label: item.label }))
      return
    }
    if (role === 'teacher') {
      const list = await teacherApi.options()
      ownerOptions.value = list.map((item) => ({
        id: item.id,
        label: `${item.name}（${item.department || '未设院系'}）`
      }))
    } else {
      const list = await studentApi.options()
      ownerOptions.value = list.map((item) => ({
        id: item.id,
        label: `${item.name}（${item.student_no}）`
      }))
    }
  } catch (err) {
    ownerOptions.value = []
  }
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, emptyForm())
  dialogVisible.value = true
  loadOwnerOptions(form.role, 'create')
}

function openEdit(row) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    ...emptyForm(),
    id: row.id,
    username: row.username,
    role: row.role,
    owner_id: row.owner_id
  })
  dialogVisible.value = true
  loadOwnerOptions(row.role, 'edit')
}

function handleRoleChange(value) {
  form.owner_id = null
  loadOwnerOptions(value, dialogMode.value)
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
    const needsOwner = form.role === 'teacher' || form.role === 'student'
    if (dialogMode.value === 'create') {
      const payload = {
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        must_change_password: form.must_change_password
      }
      if (needsOwner) payload.owner_id = form.owner_id
      await userApi.create(payload)
      ElMessage.success('账号创建成功')
    } else {
      const payload = { role: form.role }
      if (needsOwner) payload.owner_id = form.owner_id
      await userApi.update(form.id, payload)
      ElMessage.success('账号角色已更新')
      if (form.id === (userStore.user && userStore.user.id)) await userStore.fetchMe()
    }
    dialogVisible.value = false
    await loadList()
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

async function handleStatusChange(row, value) {
  const previous = row.is_active
  row.is_active = value
  try {
    const updated = await userApi.updateStatus(row.id, value)
    row.is_active = updated.is_active
    ElMessage.success(
      value ? '账号已启用' : '账号已禁用，该账号的登录已全部失效'
    )
  } catch (err) {
    row.is_active = previous
  }
}

function handleResetPassword(row) {
  ElMessageBox.prompt(
    `为账号「${row.username}」设置新的登录密码，重置后该账号其他登录会立即失效。`,
    '重置密码',
    {
      confirmButtonText: '确认重置',
      cancelButtonText: '取消',
      inputType: 'password',
      inputPlaceholder: `请输入新密码（不少于 ${minPasswordLength.value} 位）`,
      inputPattern: /^.{6,}$/,
      inputErrorMessage: '密码长度不能少于 6 位'
    }
  )
    .then(async ({ value }) => {
      await userApi.resetPassword(row.id, { new_password: value, must_change_password: true })
      ElMessage.success('密码已重置，请通知本人登录后修改')
      loadList()
    })
    .catch(() => {})
}

function handleUnbind(row) {
  ElMessageBox.confirm(
    `解除后账号「${row.username}」将不再关联「${row.owner_name}」，人员档案与成果数据保留。确认继续吗？`,
    '解除绑定',
    { confirmButtonText: '解除', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await userApi.unbind(row.id)
      ElMessage.success('已解除人员关联')
      loadList()
    })
    .catch(() => {})
}

function handleDelete(row) {
  ElMessageBox.confirm(
    `确认删除账号「${row.username}」吗？删除后无法登录，关联的人员档案与业绩成果会保留。`,
    '删除账号',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'error' }
  )
    .then(async () => {
      await userApi.remove(row.id)
      ElMessage.success('账号已删除，人员档案保留')
      loadList()
    })
    .catch(() => {})
}

onMounted(() => {
  if (!userStore.hints) userStore.fetchHints()
  loadList()
})
</script>

<style scoped>
.muted {
  color: #909399;
  font-size: 12px;
}
</style>