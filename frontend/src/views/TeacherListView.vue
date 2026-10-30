<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">教师信息管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          教师基础信息维护，可在新增时同步创建登录账号；教师账号仅能修改本人联系方式与研究方向
        </p>
      </div>
      <Button v-if="canManage" @click="openCreate">
        <Plus class="size-4" /> 新增教师
      </Button>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">关键词</Label>
          <Input
            v-model="filters.keyword"
            placeholder="姓名/职称/邮箱"
            class="w-[190px]"
            @keyup.enter="handleSearch"
          />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">院系</Label>
          <Select v-model="filters.department" @update:model-value="handleSearch">
            <SelectTrigger class="w-[170px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in departments" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">职称</Label>
          <Select v-model="filters.title" @update:model-value="handleSearch">
            <SelectTrigger class="w-[140px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in titles" :key="item" :value="item">{{ item }}</SelectItem>
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
            <TableHead class="w-[110px]">姓名</TableHead>
            <TableHead>所属院系</TableHead>
            <TableHead class="w-[100px]">职称</TableHead>
            <TableHead>邮箱</TableHead>
            <TableHead class="w-[130px]">联系电话</TableHead>
            <TableHead>关联账号</TableHead>
            <TableHead class="w-[90px]">成果数</TableHead>
            <TableHead class="w-[210px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell class="font-medium">{{ row.name }}</TableCell>
            <TableCell class="max-w-[160px] truncate text-muted-foreground">{{ row.department || '-' }}</TableCell>
            <TableCell>{{ row.title || '-' }}</TableCell>
            <TableCell class="max-w-[180px] truncate text-muted-foreground">{{ row.email || '-' }}</TableCell>
            <TableCell class="text-muted-foreground">{{ row.phone || '-' }}</TableCell>
            <TableCell>
              <div v-if="row.username" class="flex items-center gap-2">
                <Badge variant="secondary" class="text-emerald-600">{{ row.username }}</Badge>
                <button v-if="isAdmin" type="button" class="text-xs text-destructive hover:underline" @click="unbind(row)">
                  解绑
                </button>
              </div>
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
          <TableEmpty v-if="!items.length" :colspan="8">暂无教师数据</TableEmpty>
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
          <DialogTitle>{{ dialogMode === 'create' ? '新增教师' : '编辑教师' }}</DialogTitle>
          <DialogDescription>填写教师基础信息，其中电话与研究方向为可选项。</DialogDescription>
        </DialogHeader>

        <div class="space-y-3.5">
          <div class="grid gap-1.5">
            <Label>教师姓名 <span class="text-destructive">*</span></Label>
            <Input v-model="form.name" maxlength="80" placeholder="请输入教师姓名" />
          </div>
          <div class="grid gap-1.5">
            <Label>所属院系</Label>
            <Select v-model="form.department">
              <SelectTrigger><SelectValue placeholder="请选择院系" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in departments" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>职称</Label>
            <Select v-model="form.title">
              <SelectTrigger><SelectValue placeholder="请选择职称" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in titles" :key="item" :value="item">{{ item }}</SelectItem>
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
          <div class="grid gap-1.5">
            <Label>研究方向</Label>
            <Textarea v-model="form.research_area" rows="2" maxlength="200" placeholder="请输入研究方向" />
          </div>

          <template v-if="dialogMode === 'create'">
            <Separator />
            <div class="text-sm font-medium">登录账号（可选）</div>
            <div class="grid gap-1.5">
              <Label>登录名</Label>
              <Input v-model="form.username" maxlength="80" placeholder="留空则不创建账号" />
            </div>
            <div class="grid gap-1.5">
              <Label>初始密码</Label>
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

    <!-- 详情弹窗 -->
    <Dialog v-model:open="detailVisible">
      <DialogContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>教师档案</DialogTitle>
        </DialogHeader>
        <div v-if="detail" class="space-y-4">
          <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">姓名</dt><dd class="font-medium">{{ detail.name }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">职称</dt><dd>{{ detail.title || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">所属院系</dt><dd>{{ detail.department || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">登录账号</dt><dd>{{ detail.username || '未开通' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">邮箱</dt><dd>{{ detail.email || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">联系电话</dt><dd>{{ detail.phone || '-' }}</dd></div>
            <div class="flex gap-2 col-span-2"><dt class="w-20 shrink-0 text-muted-foreground">研究方向</dt><dd>{{ detail.research_area || '-' }}</dd></div>
          </dl>

          <div class="text-sm font-medium">指导学生（{{ (detail.advised_students || []).length }} 人）</div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>姓名</TableHead><TableHead>学号</TableHead><TableHead>专业</TableHead><TableHead>年级</TableHead><TableHead class="text-right">成果数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="s in detail.advised_students || []" :key="s.id || s.student_no">
                <TableCell class="font-medium">{{ s.name }}</TableCell>
                <TableCell>{{ s.student_no }}</TableCell>
                <TableCell class="text-muted-foreground">{{ s.major || '-' }}</TableCell>
                <TableCell>{{ s.grade || '-' }}</TableCell>
                <TableCell class="text-right">{{ s.achievement_count || 0 }}</TableCell>
              </TableRow>
              <TableEmpty v-if="!(detail.advised_students || []).length" :colspan="5">暂无指导学生</TableEmpty>
            </TableBody>
          </Table>

          <div class="text-sm font-medium">教师本人在读成果（{{ (detail.achievements || []).length }} 条）</div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>成果名称</TableHead><TableHead>类型</TableHead><TableHead>级别</TableHead><TableHead>年份</TableHead><TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="a in detail.achievements || []" :key="a.id">
                <TableCell class="max-w-[240px] truncate font-medium">{{ a.title }}</TableCell>
                <TableCell>{{ a.category }}</TableCell>
                <TableCell>{{ a.level }}</TableCell>
                <TableCell>{{ a.year }}</TableCell>
                <TableCell>
                  <Badge variant="secondary" :class="statusBadgeClass[a.status] || 'text-muted-foreground'">
                    {{ statusLabel(a.status) }}
                  </Badge>
                </TableCell>
              </TableRow>
              <TableEmpty v-if="!(detail.achievements || []).length" :colspan="5">暂无成果</TableEmpty>
            </TableBody>
          </Table>
        </div>
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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { metaApi, teacherApi, userApi } from '../api'
import { useUserStore } from '../stores/user'
import { statusLabel } from '../utils/file'

const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const canManage = computed(() => userStore.isAdmin || userStore.role === 'reviewer')
const minPasswordLength = computed(() => (userStore.hints && userStore.hints.min_password_length) || 6)

const statusBadgeClass = {
  draft: 'text-zinc-500',
  pending: 'text-amber-600',
  approved: 'text-emerald-600',
  rejected: 'text-destructive'
}

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const saving = ref(false)
const departments = ref([])
const titles = ref([])

const filters = reactive({ keyword: '', department: '__all__', title: '__all__', has_account: '__all__' })

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
    name: '',
    department: '',
    title: '',
    email: '',
    phone: '',
    research_area: '',
    username: '',
    password: '',
    must_change_password: false
  }
}

const form = reactive(emptyForm())

async function loadMeta() {
  try {
    const data = await metaApi.options()
    departments.value = data.departments || []
    titles.value = data.titles || []
  } catch (err) {
    // 统一错误处理
  }
}

function buildParams() {
  const params = { page: page.value, page_size: pageSize.value }
  Object.keys(filters).forEach((key) => {
    if (filters[key] !== '' && filters[key] !== '__all__') params[key] = filters[key]
  })
  return params
}

async function loadList() {
  loading.value = true
  try {
    const data = await teacherApi.list(buildParams())
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
  filters.keyword = ''
  filters.department = '__all__'
  filters.title = '__all__'
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
    name: row.name,
    department: row.department || '',
    title: row.title || '',
    email: row.email || '',
    phone: row.phone || '',
    research_area: row.research_area || ''
  })
  dialogVisible.value = true
}

async function openDetail(row) {
  detail.value = row
  detailVisible.value = true
  try {
    const data = await teacherApi.profile(row.id)
    detail.value = { ...row, ...data }
  } catch (err) {
    // 保持已有基本信息
  }
}

function viewAchievements(row) {
  router.push({ path: '/achievements', query: { owner_name: row.name, owner_type: 'teacher' } })
}

function validate() {
  if (!form.name.trim()) {
    toast.error('请输入教师姓名')
    return false
  }
  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    toast.error('邮箱格式不正确')
    return false
  }
  if (form.username.trim() && (!form.password || form.password.length < minPasswordLength.value)) {
    toast.error(`初始密码长度不能少于 ${minPasswordLength.value} 位`)
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      const payload = {
        name: form.name.trim(),
        department: form.department,
        title: form.title,
        email: form.email,
        phone: form.phone,
        research_area: form.research_area
      }
      if (form.username.trim()) {
        payload.username = form.username.trim()
        payload.password = form.password
        payload.must_change_password = form.must_change_password
      }
      await teacherApi.create(payload)
      toast.success('教师新增成功')
    } else {
      await teacherApi.update(form.id, {
        name: form.name.trim(),
        department: form.department,
        title: form.title,
        email: form.email,
        phone: form.phone,
        research_area: form.research_area
      })
      toast.success('教师信息已更新')
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

function unbind(row) {
  askConfirm({
    title: '解绑账号',
    description: `解绑后「${row.username}」将无法再登录查看该教师档案，确认继续吗？`,
    confirmText: '解绑',
    danger: false,
    handler: async () => {
      await userApi.unbind(row.user_id)
      toast.success('已解绑账号')
      loadList()
    }
  })
}

function handleDelete(row) {
  askConfirm({
    title: '删除确认',
    description: `确认删除教师「${row.name}」吗？其 ${row.achievement_count} 条成果、支撑材料、指导关系以及登录账号将一并删除，且不可恢复。`,
    confirmText: '删除',
    danger: true,
    handler: async () => {
      await teacherApi.remove(row.id)
      toast.success('教师已删除')
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