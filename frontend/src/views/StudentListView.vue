<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">学生信息管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          学生基础信息与指导教师维护；学生账号仅能修改本人联系方式，学号/年级/专业等由管理员维护
        </p>
      </div>
      <Button v-if="canManage" @click="openCreate"><Plus class="size-4" /> 新增学生</Button>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">关键词</Label>
          <Input v-model="filters.keyword" placeholder="姓名/学号/邮箱" class="w-[190px]" @keyup.enter="handleSearch" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">年级</Label>
          <Select v-model="filters.grade" @update:model-value="handleSearch">
            <SelectTrigger class="w-[130px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in grades" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">专业</Label>
          <Select v-model="filters.major" @update:model-value="handleSearch">
            <SelectTrigger class="w-[170px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in majors" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">指导教师</Label>
          <Select v-model="filters.advisor_id" @update:model-value="handleSearch">
            <SelectTrigger class="w-[160px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in teacherOptions" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">账号</Label>
          <Select v-model="filters.has_account" @update:model-value="handleSearch">
            <SelectTrigger class="w-[120px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem value="1">已开通</SelectItem>
              <SelectItem value="0">未开通</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex gap-2">
          <Button @click="handleSearch"><Search class="size-4" /> 查询</Button>
          <Button variant="outline" @click="handleReset"><RotateCcw class="size-4" /> 重置</Button>
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[120px]">学号</TableHead>
            <TableHead class="w-[100px]">姓名</TableHead>
            <TableHead class="w-[90px]">年级</TableHead>
            <TableHead>专业</TableHead>
            <TableHead class="w-[110px]">班级</TableHead>
            <TableHead>指导教师</TableHead>
            <TableHead class="w-[120px]">账号</TableHead>
            <TableHead class="w-[90px]">成果数</TableHead>
            <TableHead class="w-[210px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell class="text-muted-foreground">{{ row.student_no }}</TableCell>
            <TableCell class="font-medium">{{ row.name }}</TableCell>
            <TableCell>{{ row.grade || '-' }}</TableCell>
            <TableCell class="max-w-[140px] truncate text-muted-foreground">{{ row.major || '-' }}</TableCell>
            <TableCell>{{ row.class_name || '-' }}</TableCell>
            <TableCell class="max-w-[130px] truncate text-muted-foreground">{{ row.advisor_names || '未指定' }}</TableCell>
            <TableCell>
              <Badge v-if="row.username" variant="secondary" class="text-emerald-600">{{ row.username }}</Badge>
              <span v-else class="text-muted-foreground">未开通</span>
            </TableCell>
            <TableCell>{{ row.achievement_count || 0 }}</TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="openDetail(row)">详情</Button>
                <Button variant="ghost" size="sm" @click="viewAchievements(row)">成果</Button>
                <template v-if="canManage">
                  <Button variant="ghost" size="sm" @click="openEdit(row)">编辑</Button>
                  <Button v-if="isAdmin" variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="handleDelete(row)">
                    删除
                  </Button>
                </template>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="9">暂无学生数据</TableEmpty>
        </TableBody>
      </Table>

      <div class="border-t px-4 py-3">
        <AppPagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="sm:max-w-[620px]">
        <DialogHeader>
          <DialogTitle>{{ dialogMode === 'create' ? '新增学生' : '编辑学生' }}</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="grid gap-1.5">
            <Label>学号 <span class="text-destructive">*</span></Label>
            <Input v-model="form.student_no" maxlength="50" placeholder="请输入学号" />
          </div>
          <div class="grid gap-1.5">
            <Label>姓名 <span class="text-destructive">*</span></Label>
            <Input v-model="form.name" maxlength="80" placeholder="请输入姓名" />
          </div>
          <div class="grid gap-1.5">
            <Label>年级</Label>
            <Select v-model="form.grade">
              <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in grades" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>班级</Label>
            <Input v-model="form.class_name" maxlength="80" placeholder="请输入班级" />
          </div>
          <div class="grid gap-1.5">
            <Label>专业</Label>
            <Select v-model="form.major">
              <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in majors" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>所属院系</Label>
            <Select v-model="form.department">
              <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in departments" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>邮箱</Label>
            <Input v-model="form.email" maxlength="120" placeholder="请输入邮箱" />
          </div>
          <div class="grid gap-1.5">
            <Label>联系电话</Label>
            <Input v-model="form.phone" maxlength="30" placeholder="请输入联系电话" />
          </div>
        </div>

        <Separator />
        <div class="text-sm font-medium">指导教师（第一位为主导师）</div>
        <div class="max-h-[180px] space-y-1 overflow-auto rounded-md border p-2">
          <label v-for="item in teacherOptions" :key="item.id" class="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-muted">
            <Checkbox :checked="form.advisor_ids.includes(item.id)" @update:checked="toggleAdvisor(item.id)" />
            <span class="text-sm">{{ item.label }}</span>
          </label>
          <p v-if="!teacherOptions.length" class="px-2 py-1 text-sm text-muted-foreground">暂无教师可选</p>
        </div>

        <template v-if="dialogMode === 'create'">
          <Separator />
          <div class="text-sm font-medium">登录账号（可选）</div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="grid gap-1.5">
              <Label>登录名</Label>
              <Input v-model="form.username" maxlength="80" placeholder="留空则不创建账号" />
            </div>
            <div class="grid gap-1.5">
              <Label>初始密码</Label>
              <Input v-model="form.password" type="password" :placeholder="`长度不少于 ${minPasswordLength} 位`" />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Switch :checked="form.must_change_password" @update:checked="form.must_change_password = $event" />
            <span class="text-sm text-muted-foreground">开启后该账号首次登录需修改密码</span>
          </div>
        </template>

        <DialogFooter>
          <Button variant="outline" @click="dialogVisible = false">取消</Button>
          <Button :disabled="saving" @click="handleSubmit">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 详情弹窗 -->
    <Dialog v-model:open="detailVisible">
      <DialogContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>学生档案</DialogTitle>
        </DialogHeader>
        <dl v-if="detail" class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">姓名</dt><dd class="font-medium">{{ detail.name }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">学号</dt><dd>{{ detail.student_no }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">年级</dt><dd>{{ detail.grade || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">班级</dt><dd>{{ detail.class_name || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">专业</dt><dd>{{ detail.major || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">院系</dt><dd>{{ detail.department || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">邮箱</dt><dd>{{ detail.email || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">电话</dt><dd>{{ detail.phone || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">账号</dt><dd>{{ detail.username || '未开通' }}</dd></div>
          <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">指导教师</dt><dd>{{ detail.advisor_names || '未指定' }}</dd></div>
        </dl>

        <div class="mt-4 text-sm font-medium">业绩成果（{{ (detail.achievements || []).length }} 条）</div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>成果名称</TableHead><TableHead class="w-[110px]">类型</TableHead><TableHead class="w-[90px]">级别</TableHead><TableHead class="w-[80px]">年份</TableHead><TableHead class="w-[90px]">状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in detail.achievements || []" :key="row.id">
              <TableCell class="max-w-[200px] truncate font-medium">{{ row.title }}</TableCell>
              <TableCell>{{ row.category }}</TableCell>
              <TableCell>{{ row.level || '-' }}</TableCell>
              <TableCell>{{ row.year }}</TableCell>
              <TableCell>
                <Badge variant="secondary" :class="statusBadgeClass[row.status] || 'text-muted-foreground'">{{ statusLabel(row.status) }}</Badge>
              </TableCell>
            </TableRow>
            <TableEmpty v-if="!(detail.achievements || []).length" :colspan="5">暂无成果</TableEmpty>
          </TableBody>
        </Table>
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
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Plus, RotateCcw, Search } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { metaApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'
import { statusLabel } from '../utils/file'

const statusBadgeClass = {
  draft: 'text-zinc-500',
  pending: 'text-amber-600',
  approved: 'text-emerald-600',
  rejected: 'text-destructive'
}

const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const canManage = computed(() => userStore.isAdmin || userStore.role === 'reviewer')
const minPasswordLength = computed(() => (userStore.hints && userStore.hints.min_password_length) || 6)

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
  grade: '__all__',
  major: '__all__',
  advisor_id: '__all__',
  has_account: '__all__'
})

const dialogVisible = ref(false)
const dialogMode = ref('create')
const detailVisible = ref(false)
const detail = ref(null)

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
      if (filters[key] !== '' && filters[key] !== '__all__') params[key] = filters[key]
    })
    if (filters.advisor_id !== '__all__') params.advisor_id = Number(filters.advisor_id)
    const data = await studentApi.list(params)
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
    filters[key] = ''
  })
  filters.grade = '__all__'
  filters.major = '__all__'
  filters.advisor_id = '__all__'
  filters.has_account = '__all__'
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

function toggleAdvisor(id) {
  const i = form.advisor_ids.indexOf(id)
  if (i >= 0) form.advisor_ids.splice(i, 1)
  else form.advisor_ids.push(id)
}

function validate() {
  if (!form.student_no.trim()) {
    toast.error('请输入学号')
    return false
  }
  if (!form.name.trim()) {
    toast.error('请输入学生姓名')
    return false
  }
  if (dialogMode.value === 'create' && form.username.trim() && (!form.password || form.password.length < minPasswordLength.value)) {
    toast.error(`初始密码长度不能少于 ${minPasswordLength.value} 位`)
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
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
      toast.success('学生新增成功')
    } else {
      await studentApi.update(form.id, payload)
      toast.success('学生信息已更新')
    }
    dialogVisible.value = false
    await loadList()
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
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

function handleDelete(row) {
  askConfirm({
    title: '删除确认',
    description: `确认删除学生「${row.name}」吗？其 ${row.achievement_count} 条成果、支撑材料、指导关系以及登录账号将一并删除，且不可恢复。`,
    confirmText: '删除',
    danger: true,
    handler: async () => {
      await studentApi.remove(row.id)
      toast.success('学生已删除')
      if (items.value.length === 1 && page.value > 1) page.value -= 1
      loadList()
    }
  })
}

onMounted(() => {
  loadMeta()
  loadList()
})
</script>