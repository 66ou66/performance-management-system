<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">{{ isTeacher ? '我的指导学生' : '指导关系管理' }}</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          建立教师与学生之间的指导关系后，教师的教学业绩可与学生的竞赛、论文等成果自动关联
        </p>
      </div>
      <Button v-if="isAdmin" @click="openCreate"><Plus class="size-4" /> 新增指导关系</Button>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div v-if="!isTeacher" class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">指导教师</Label>
          <Select v-model="teacherId" @update:model-value="handleSearch">
            <SelectTrigger class="w-[200px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in teachers" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">学生</Label>
          <Select v-model="studentId" @update:model-value="handleSearch">
            <SelectTrigger class="w-[200px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in students" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" @click="loadList"><RefreshCw class="size-4" /> 刷新</Button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[150px]">指导教师</TableHead>
            <TableHead class="w-[150px]">学生</TableHead>
            <TableHead class="w-[100px]">主导师</TableHead>
            <TableHead class="w-[100px]">起始年份</TableHead>
            <TableHead class="w-[100px]">结束年份</TableHead>
            <TableHead>备注</TableHead>
            <TableHead class="w-[110px]">指导成果</TableHead>
            <TableHead v-if="isAdmin" class="w-[180px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell class="font-medium">{{ row.teacher_name }}</TableCell>
            <TableCell>{{ row.student_name }}</TableCell>
            <TableCell>
              <Badge v-if="row.is_primary" variant="secondary" class="text-emerald-600">主导师</Badge>
              <span v-else class="text-muted-foreground">-</span>
            </TableCell>
            <TableCell>{{ row.start_year || '-' }}</TableCell>
            <TableCell>{{ row.end_year || '-' }}</TableCell>
            <TableCell class="max-w-[160px] truncate text-muted-foreground">{{ row.note || '-' }}</TableCell>
            <TableCell>
              <Button variant="link" class="h-auto p-0" @click="viewAchievements(row)">查看成果</Button>
            </TableCell>
            <TableCell v-if="isAdmin" class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="togglePrimary(row)">
                  {{ row.is_primary ? '取消主导师' : '设为主导师' }}
                </Button>
                <Button variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="remove(row)">解除</Button>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="isAdmin ? 8 : 7">暂无指导关系</TableEmpty>
        </TableBody>
      </Table>

      <div class="border-t px-4 py-3">
        <AppPagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" />
      </div>
    </div>

    <!-- 新增弹窗 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>新增指导关系</DialogTitle>
        </DialogHeader>
        <div class="space-y-3.5">
          <div class="grid gap-1.5">
            <Label>指导教师 <span class="text-destructive">*</span></Label>
            <Select v-model="form.teacher_id">
              <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in teachers" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>学生 <span class="text-destructive">*</span></Label>
            <Select v-model="form.student_id">
              <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in students" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex items-center gap-2">
            <Switch :checked="form.is_primary" @update:checked="form.is_primary = $event" />
            <span class="text-sm text-muted-foreground">主导师</span>
          </div>
          <div class="grid gap-1.5">
            <Label>起始年份</Label>
            <Input v-model="form.start_year" type="number" placeholder="例如 2026" />
          </div>
          <div class="grid gap-1.5">
            <Label>备注</Label>
            <Input v-model="form.note" maxlength="200" placeholder="备注信息" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="dialogVisible = false">取消</Button>
          <Button :disabled="saving" @click="handleSubmit">保存</Button>
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
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Plus, RefreshCw } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
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
const teacherId = ref('__all__')
const studentId = ref('__all__')
const teachers = ref([])
const students = ref([])

const dialogVisible = ref(false)
const saving = ref(false)
const form = reactive({ teacher_id: '', student_id: '', is_primary: false, start_year: '', note: '' })

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

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
    if (teacherId.value !== '__all__') params.teacher_id = Number(teacherId.value)
    if (studentId.value !== '__all__') params.student_id = Number(studentId.value)
    const data = await advisorApi.list(params)
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

function openCreate() {
  Object.assign(form, {
    teacher_id: teacherId.value !== '__all__' ? teacherId.value : '',
    student_id: studentId.value !== '__all__' ? studentId.value : '',
    is_primary: false,
    start_year: String(new Date().getFullYear()),
    note: ''
  })
  dialogVisible.value = true
}

function validate() {
  if (!form.teacher_id) {
    toast.error('请选择指导教师')
    return false
  }
  if (!form.student_id) {
    toast.error('请选择学生')
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  saving.value = true
  try {
    await advisorApi.create({
      teacher_id: Number(form.teacher_id),
      student_id: Number(form.student_id),
      is_primary: form.is_primary,
      start_year: form.start_year ? Number(form.start_year) : null,
      note: form.note
    })
    toast.success('指导关系已新增')
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
    toast.success('已更新')
    loadList()
  } catch (err) {
    // 统一错误处理
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

function remove(row) {
  askConfirm({
    title: '解除确认',
    description: `确认解除「${row.teacher_name}」与「${row.student_name}」的指导关系吗？`,
    confirmText: '解除',
    danger: false,
    handler: async () => {
      await advisorApi.remove(row.id)
      toast.success('已解除')
      loadList()
    }
  })
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