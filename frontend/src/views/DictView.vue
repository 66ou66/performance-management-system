<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">基础字典管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          院系 / 专业 / 职称 / 年级的规范取值。统一字典可避免“计算机学院”与“计算机学院 ”被统计成两个院系
        </p>
      </div>
      <Button @click="openCreate"><Plus class="size-4" /> 新增字典项</Button>
    </div>

    <!-- 类型切换 -->
    <div class="inline-flex flex-wrap items-center gap-1 rounded-lg border bg-muted p-1">
      <Button
        v-for="kind in kinds"
        :key="kind.value"
        :variant="activeKind === kind.value ? 'default' : 'ghost'"
        size="sm"
        @click="activeKind = kind.value; loadUsage()"
      >
        {{ kind.label }}
      </Button>
    </div>

    <!-- 双栏 -->
    <div class="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
      <div class="rounded-xl border bg-white shadow-sm">
        <div class="border-b px-4 py-3 text-sm font-medium">已登记取值</div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>别名</TableHead>
              <TableHead class="w-[120px]">上级</TableHead>
              <TableHead class="w-[70px]">排序</TableHead>
              <TableHead class="w-[80px]">状态</TableHead>
              <TableHead class="w-[150px] text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in currentItems" :key="row.id">
              <TableCell class="font-medium">{{ row.name }}</TableCell>
              <TableCell class="max-w-[140px] truncate text-muted-foreground">
                {{ row.aliases && row.aliases.length ? row.aliases.join('、') : '-' }}
              </TableCell>
              <TableCell class="text-muted-foreground">{{ row.parent_name || '-' }}</TableCell>
              <TableCell>{{ row.sort_order }}</TableCell>
              <TableCell>
                <Badge :variant="row.is_active ? 'secondary' : 'outline'" :class="row.is_active ? 'text-emerald-600' : 'text-muted-foreground'">
                  {{ row.is_active ? '启用' : '停用' }}
                </Badge>
              </TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" @click="openEdit(row)">编辑</Button>
                  <Button variant="ghost" size="sm" @click="openMerge(row)">合并</Button>
                  <Button variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="remove(row)">删除</Button>
                </div>
              </TableCell>
            </TableRow>
            <TableEmpty v-if="!currentItems.length" :colspan="6">暂无字典项</TableEmpty>
          </TableBody>
        </Table>
      </div>

      <div class="rounded-xl border bg-white shadow-sm">
        <div class="border-b px-4 py-3">
          <div class="text-sm font-medium">数据中实际出现的取值</div>
          <p class="mt-0.5 text-xs text-muted-foreground">
            标记为「未登记」的取值建议补充进字典，或合并到已有取值上，以免统计口径分裂。
          </p>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>取值</TableHead>
              <TableHead class="w-[80px]">记录数</TableHead>
              <TableHead class="w-[90px]">状态</TableHead>
              <TableHead class="w-[90px] text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in usageRows" :key="row.name">
              <TableCell class="max-w-[130px] truncate font-medium">{{ row.name }}</TableCell>
              <TableCell>{{ row.count }}</TableCell>
              <TableCell>
                <Badge :variant="row.registered ? 'secondary' : 'outline'" :class="row.registered ? 'text-emerald-600' : 'text-amber-600'">
                  {{ row.registered ? '已登记' : '未登记' }}
                </Badge>
              </TableCell>
              <TableCell class="text-right">
                <Button v-if="!row.registered" variant="ghost" size="sm" @click="quickRegister(row)">登记</Button>
              </TableCell>
            </TableRow>
            <TableEmpty v-if="!usageRows.length" :colspan="4">暂无数据</TableEmpty>
          </TableBody>
        </Table>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>{{ form.id ? '编辑字典项' : '新增字典项' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-3.5">
          <div class="grid gap-1.5">
            <Label>类型</Label>
            <Input :model-value="kindLabel(form.kind)" disabled />
          </div>
          <div class="grid gap-1.5">
            <Label>名称 <span class="text-destructive">*</span></Label>
            <Input v-model="form.name" maxlength="120" placeholder="请输入字典项名称" />
          </div>
          <div class="grid gap-1.5">
            <Label>别名</Label>
            <Input v-model="form.aliases" placeholder="多个别名用逗号分隔，导入/录入时会自动归一" />
          </div>
          <div v-if="form.kind === 'major'" class="grid gap-1.5">
            <Label>所属院系</Label>
            <Select v-model="form.parent_name">
              <SelectTrigger><SelectValue placeholder="请选择院系" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in departmentNames" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>排序</Label>
            <Input v-model.number="form.sort_order" type="number" />
          </div>
          <div class="flex items-center gap-2">
            <Switch :checked="form.is_active" @update:checked="form.is_active = $event" />
            <span class="text-sm text-muted-foreground">启用</span>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="dialogVisible = false">取消</Button>
          <Button :disabled="saving" @click="handleSubmit">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 合并弹窗 -->
    <Dialog v-model:open="mergeDialogVisible">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>合并字典项</DialogTitle>
          <DialogDescription>
            将「{{ mergeSource && mergeSource.name }}」合并到其它取值：现有数据会被改写，源字典项将被删除。
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-1.5">
          <Label>目标取值</Label>
          <Select v-model="mergeTargetId">
            <SelectTrigger><SelectValue placeholder="请选择目标字典项" /></SelectTrigger>
            <SelectContent>
              <SelectItem v-for="item in mergeOptions" :key="item.id" :value="String(item.id)">{{ item.name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="mergeDialogVisible = false">取消</Button>
          <Button @click="confirmMerge">确认合并</Button>
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
import { Plus } from 'lucide-vue-next'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { dictApi, metaApi } from '../api'

const kinds = ref([
  { value: 'department', label: '院系' },
  { value: 'major', label: '专业' },
  { value: 'title', label: '职称' },
  { value: 'grade', label: '年级' }
])
const activeKind = ref('department')
const grouped = ref({})
const usage = ref({})
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const mergeDialogVisible = ref(false)
const mergeSource = ref(null)
const mergeTargetId = ref('')
const mergeOptions = ref([])
const form = reactive({
  id: null,
  kind: 'department',
  name: '',
  aliases: '',
  parent_name: '',
  sort_order: 0,
  is_active: true
})

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

const currentItems = computed(() => grouped.value[activeKind.value] || [])
const usageRows = computed(() => usage.value[activeKind.value] || [])
const departmentNames = computed(() => (grouped.value.department || []).map((item) => item.name))

function kindLabel(kind) {
  const found = kinds.value.find((item) => item.value === kind)
  return found ? found.label : kind
}

async function loadAll() {
  loading.value = true
  try {
    const data = await metaApi.options()
    if (data.dict_kinds && data.dict_kinds.length) kinds.value = data.dict_kinds
    grouped.value = await dictApi.grouped()
    usage.value = await dictApi.usage()
  } catch (err) {
    grouped.value = {}
  } finally {
    loading.value = false
  }
}

async function loadUsage() {
  try {
    usage.value = await dictApi.usage()
    grouped.value = await dictApi.grouped()
  } catch (err) {
    // 统一错误处理
  }
}

function openCreate() {
  Object.assign(form, {
    id: null,
    kind: activeKind.value,
    name: '',
    aliases: '',
    parent_name: '',
    sort_order: currentItems.value.length + 1,
    is_active: true
  })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    kind: row.kind,
    name: row.name,
    aliases: (row.aliases || []).join(','),
    parent_name: row.parent_name || '',
    sort_order: row.sort_order || 0,
    is_active: row.is_active !== false
  })
  dialogVisible.value = true
}

function quickRegister(row) {
  Object.assign(form, {
    id: null,
    kind: activeKind.value,
    name: row.name,
    aliases: '',
    parent_name: '',
    sort_order: currentItems.value.length + 1,
    is_active: true
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.name.trim()) {
    toast.error('请输入字典项名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      kind: form.kind,
      name: form.name.trim(),
      aliases: form.aliases,
      parent_name: form.parent_name,
      sort_order: form.sort_order || 0,
      is_active: form.is_active
    }
    if (form.id) {
      await dictApi.update(form.id, payload)
      toast.success('字典项已更新')
    } else {
      await dictApi.create(payload)
      toast.success('字典项已新增')
    }
    dialogVisible.value = false
    loadUsage()
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

function openMerge(row) {
  const options = currentItems.value.filter((item) => item.id !== row.id)
  if (!options.length) {
    toast.warning('没有可合并的目标字典项')
    return
  }
  mergeOptions.value = options
  mergeSource.value = row
  mergeTargetId.value = ''
  mergeDialogVisible.value = true
}

async function confirmMerge() {
  if (!mergeTargetId.value) {
    toast.error('请选择目标字典项')
    return
  }
  const data = await dictApi.merge(mergeSource.value.id, Number(mergeTargetId.value))
  toast.success(`已合并，更新了 ${data.affected} 条数据`)
  mergeDialogVisible.value = false
  loadUsage()
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
    title: '删除确认',
    description: `确认删除字典项「${row.name}」吗？存量数据中的取值不会被清除。`,
    confirmText: '删除',
    danger: true,
    handler: async () => {
      await dictApi.remove(row.id)
      toast.success('字典项已删除')
      loadUsage()
    }
  })
}

onMounted(loadAll)
</script>