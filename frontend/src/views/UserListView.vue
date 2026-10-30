<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">账号权限管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          管理登录账号、角色权限（管理员 / 审核员 / 教师 / 学生）、启用状态与密码重置
        </p>
      </div>
      <Button @click="openCreate"><Plus class="size-4" /> 新增账号</Button>
    </div>

    <!-- 筛选 -->
    <div class="space-y-4">
      <Alert>
        <ShieldAlert class="size-4" />
        <AlertTitle>权限说明</AlertTitle>
        <AlertDescription>
          管理员拥有全部权限；审核员可审核成果、查看全部档案但不能删除人员；教师仅能维护本人成果（含「指导学生成果」类别）；学生仅能维护本人成果。
        </AlertDescription>
      </Alert>

      <div class="rounded-xl border bg-white p-4 shadow-sm">
        <div class="flex flex-wrap items-end gap-3">
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">关键词</Label>
            <Input v-model="filters.keyword" placeholder="登录名/人员姓名" class="w-[180px]" @keyup.enter="handleSearch" />
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">角色</Label>
            <Select v-model="filters.role" @update:model-value="handleSearch">
              <SelectTrigger class="w-[130px]"><SelectValue placeholder="全部" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                <SelectItem value="admin">管理员</SelectItem>
                <SelectItem value="reviewer">审核员</SelectItem>
                <SelectItem value="teacher">教师</SelectItem>
                <SelectItem value="student">学生</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">状态</Label>
            <Select v-model="filters.status" @update:model-value="handleSearch">
              <SelectTrigger class="w-[120px]"><SelectValue placeholder="全部" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                <SelectItem value="1">启用</SelectItem>
                <SelectItem value="0">禁用</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">人员绑定</Label>
            <Select v-model="filters.linked" @update:model-value="handleSearch">
              <SelectTrigger class="w-[130px]"><SelectValue placeholder="全部" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                <SelectItem value="1">已绑定</SelectItem>
                <SelectItem value="0">未绑定</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex gap-2">
            <Button @click="handleSearch"><Search class="size-4" /> 查询</Button>
            <Button variant="outline" @click="handleReset"><RotateCcw class="size-4" /> 重置</Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>登录名</TableHead>
            <TableHead class="w-[110px]">角色</TableHead>
            <TableHead>关联人员</TableHead>
            <TableHead class="w-[120px]">密码状态</TableHead>
            <TableHead class="w-[120px]">状态</TableHead>
            <TableHead class="w-[165px]">最近登录</TableHead>
            <TableHead class="w-[165px]">创建时间</TableHead>
            <TableHead class="w-[240px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell class="font-medium">{{ row.username }}</TableCell>
            <TableCell>
              <Badge variant="secondary" :class="roleBadgeClass[row.role] || 'text-muted-foreground'">{{ roleLabel(row.role) }}</Badge>
            </TableCell>
            <TableCell>
              <template v-if="row.owner_name">
                <span>{{ row.owner_name }}</span>
                <Badge variant="outline" class="ml-1.5 text-muted-foreground">{{ ownerTypeLabel(row.owner_type) }}</Badge>
              </template>
              <span v-else class="text-muted-foreground">-</span>
            </TableCell>
            <TableCell>
              <Badge v-if="row.must_change_password" variant="secondary" class="text-amber-600">待修改</Badge>
              <span v-else class="text-muted-foreground">已设置</span>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-2">
                <Switch
                  :checked="row.is_active"
                  :disabled="row.id === (userStore.user && userStore.user.id)"
                  @update:checked="(value) => handleStatusChange(row, value)"
                />
                <span class="text-sm text-muted-foreground">{{ row.is_active ? '启用' : '禁用' }}</span>
              </div>
            </TableCell>
            <TableCell class="text-muted-foreground">{{ row.last_login_at || '从未登录' }}</TableCell>
            <TableCell class="text-muted-foreground">{{ row.created_at }}</TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="openEdit(row)">编辑</Button>
                <Button variant="ghost" size="sm" class="text-amber-600" @click="openResetPassword(row)">重置密码</Button>
                <Button v-if="row.owner_type" variant="ghost" size="sm" @click="handleUnbind(row)">解绑</Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="text-destructive hover:text-destructive"
                  :disabled="row.id === (userStore.user && userStore.user.id)"
                  @click="handleDelete(row)"
                >
                  删除
                </Button>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="8">暂无账号数据</TableEmpty>
        </TableBody>
      </Table>

      <div class="border-t px-4 py-3">
        <AppPagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>{{ dialogMode === 'create' ? '新增账号' : '编辑账号角色' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-3.5">
          <div class="grid gap-1.5">
            <Label>登录名 <span class="text-destructive">*</span></Label>
            <Input v-model="form.username" maxlength="80" :disabled="dialogMode === 'edit'" placeholder="请输入登录名" />
          </div>
          <div class="grid gap-1.5">
            <Label>角色 <span class="text-destructive">*</span></Label>
            <Select v-model="form.role" @update:model-value="handleRoleChange">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">管理员</SelectItem>
                <SelectItem value="reviewer">审核员</SelectItem>
                <SelectItem value="teacher">教师</SelectItem>
                <SelectItem value="student">学生</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div v-if="form.role === 'teacher' || form.role === 'student'" class="grid gap-1.5">
            <Label>关联人员 <span class="text-destructive">*</span></Label>
            <Select :model-value="form.owner_id == null ? '' : String(form.owner_id)" @update:model-value="form.owner_id = $event ? Number($event) : null">
              <SelectTrigger><SelectValue placeholder="请选择关联人员" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in ownerOptions" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Alert v-else>
            <Info class="size-4" />
            <AlertDescription>
              {{ form.role === 'reviewer' ? '审核员不绑定具体人员档案，可查看全部档案并审核成果。' : '管理员账号拥有全部权限，请谨慎分配。' }}
            </AlertDescription>
          </Alert>
          <template v-if="dialogMode === 'create'">
            <div class="grid gap-1.5">
              <Label>登录密码 <span class="text-destructive">*</span></Label>
              <Input v-model="form.password" type="password" :placeholder="`长度不少于 ${minPasswordLength} 位`" />
            </div>
            <div class="flex items-center gap-2">
              <Switch :checked="form.must_change_password" @update:checked="form.must_change_password = $event" />
              <span class="text-sm text-muted-foreground">开启后该账号首次登录需修改密码</span>
            </div>
          </template>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="dialogVisible = false">取消</Button>
          <Button :disabled="saving" @click="handleSubmit">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 重置密码弹窗 -->
    <Dialog v-model:open="resetDialogVisible">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>重置密码</DialogTitle>
          <DialogDescription>
            为账号「{{ resetTarget && resetTarget.username }}」设置新的登录密码，重置后该账号其他登录会立即失效。
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-1.5">
          <Label>新密码</Label>
          <Input v-model="resetPassword" type="password" :placeholder="`请输入新密码（不少于 ${minPasswordLength} 位）`" />
        </div>
        <DialogFooter>
          <Button variant="outline" @click="resetDialogVisible = false">取消</Button>
          <Button @click="confirmResetPassword">确认重置</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 确认弹窗 -->
    <ConfirmDialog
      v-model:open="confirmState.open"
      :title="confirmState.title"
      :description="confirmState.description"
      :confirm-text="confirmState.confirmText"
      :danger="confirmState.danger"
      @confirm="onConfirm"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Info, Plus, RotateCcw, Search, ShieldAlert } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { studentApi, teacherApi, userApi } from '../api'
import { useUserStore } from '../stores/user'
import { ownerTypeLabel, roleLabel } from '../utils/file'

const roleBadgeClass = {
  admin: 'text-blue-600',
  reviewer: 'text-violet-600',
  teacher: 'text-emerald-600',
  student: 'text-amber-600'
}

const userStore = useUserStore()
const minPasswordLength = computed(() => (userStore.hints && userStore.hints.min_password_length) || 6)

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const saving = ref(false)

const filters = reactive({ keyword: '', role: '__all__', status: '__all__', linked: '__all__' })

const dialogVisible = ref(false)
const dialogMode = ref('create')
const ownerOptions = ref([])
const resetDialogVisible = ref(false)
const resetTarget = ref(null)
const resetPassword = ref('')

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

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

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    Object.keys(filters).forEach((key) => {
      if (filters[key] !== '' && filters[key] !== '__all__') params[key] = filters[key]
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
    filters[key] = '__all__'
  })
  filters.keyword = ''
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
      ownerOptions.value = list.map((item) => ({ id: item.id, label: `${item.name}（${item.department || '未设院系'}）` }))
    } else {
      const list = await studentApi.options()
      ownerOptions.value = list.map((item) => ({ id: item.id, label: `${item.name}（${item.student_no}）` }))
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

function validate() {
  if (!form.username.trim()) {
    toast.error('请输入登录名')
    return false
  }
  if (!form.role) {
    toast.error('请选择角色')
    return false
  }
  if ((form.role === 'teacher' || form.role === 'student') && !form.owner_id) {
    toast.error('请选择关联人员')
    return false
  }
  if (dialogMode.value === 'create' && (!form.password || form.password.length < minPasswordLength.value)) {
    toast.error(`登录密码长度不能少于 ${minPasswordLength.value} 位`)
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
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
      toast.success('账号创建成功')
    } else {
      const payload = { role: form.role }
      if (needsOwner) payload.owner_id = form.owner_id
      await userApi.update(form.id, payload)
      toast.success('账号角色已更新')
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
    toast.success(value ? '账号已启用' : '账号已禁用，该账号的登录已全部失效')
  } catch (err) {
    row.is_active = previous
  }
}

function openResetPassword(row) {
  resetTarget.value = row
  resetPassword.value = ''
  resetDialogVisible.value = true
}

async function confirmResetPassword() {
  if (!resetPassword.value || resetPassword.value.length < minPasswordLength.value) {
    toast.error(`密码长度不能少于 ${minPasswordLength.value} 位`)
    return
  }
  await userApi.resetPassword(resetTarget.value.id, { new_password: resetPassword.value, must_change_password: true })
  toast.success('密码已重置，请通知本人登录后修改')
  resetDialogVisible.value = false
  loadList()
}

function askConfirm({ title, description, confirmText, danger, handler }) {
  confirmState.title = title
  confirmState.description = description
  confirmState.confirmText = confirmText
  confirmState.danger = danger
  confirmState.handler = handler
  confirmState.open = true
}

function onConfirm() {
  confirmState.open = false
  const handler = confirmState.handler
  confirmState.handler = null
  if (handler) handler()
}

function handleUnbind(row) {
  askConfirm({
    title: '解除绑定',
    description: `解除后账号「${row.username}」将不再关联「${row.owner_name}」，人员档案与成果数据保留。确认继续吗？`,
    confirmText: '解除',
    danger: false,
    handler: async () => {
      await userApi.unbind(row.id)
      toast.success('已解除人员关联')
      loadList()
    }
  })
}

function handleDelete(row) {
  askConfirm({
    title: '删除账号',
    description: `确认删除账号「${row.username}」吗？删除后无法登录，关联的人员档案与业绩成果会保留。`,
    confirmText: '删除',
    danger: true,
    handler: async () => {
      await userApi.remove(row.id)
      toast.success('账号已删除，人员档案保留')
      loadList()
    }
  })
}

onMounted(() => {
  if (!userStore.hints) userStore.fetchHints()
  loadList()
})
</script>