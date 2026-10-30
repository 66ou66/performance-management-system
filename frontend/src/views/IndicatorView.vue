<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">认证指标点管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          工程教育认证毕业要求指标点：用于把教师与学生的业绩成果挂接到具体毕业要求，形成达成度支撑
        </p>
      </div>
      <div class="flex gap-2">
        <Button variant="outline" @click="loadAll"><RefreshCw class="size-4" /> 刷新</Button>
        <Button @click="openCreate"><Plus class="size-4" /> 新增指标点</Button>
      </div>
    </div>

    <!-- 覆盖度提示 -->
    <Alert v-if="coverage">
      <Info class="size-4" />
      <AlertTitle>指标点覆盖情况</AlertTitle>
      <AlertDescription>
        当前统计口径下共 {{ coverage.total_achievements }} 条成果，
        其中 {{ coverage.covered_achievements }} 条已关联指标点（覆盖率
        {{ coverage.coverage_percent }}%）；未覆盖指标点：
        {{ coverage.uncovered_indicators.length ? coverage.uncovered_indicators.join('、') : '无' }}
      </AlertDescription>
    </Alert>

    <!-- 表格 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[80px]">编号</TableHead>
            <TableHead class="w-[200px]">指标点名称</TableHead>
            <TableHead>说明</TableHead>
            <TableHead class="w-[110px]">关联成果</TableHead>
            <TableHead class="w-[80px]">排序</TableHead>
            <TableHead class="w-[90px]">状态</TableHead>
            <TableHead class="w-[170px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell>{{ row.code }}</TableCell>
            <TableCell class="font-medium">{{ row.name }}</TableCell>
            <TableCell class="max-w-[300px] truncate text-muted-foreground">{{ row.description || '-' }}</TableCell>
            <TableCell>
              <Button variant="link" class="h-auto p-0" @click="viewAchievements(row)">
                {{ row.achievement_count || 0 }} 条
              </Button>
            </TableCell>
            <TableCell>{{ row.sort_order }}</TableCell>
            <TableCell>
              <Badge :variant="row.is_active ? 'secondary' : 'outline'" :class="row.is_active ? 'text-emerald-600' : 'text-muted-foreground'">
                {{ row.is_active ? '启用' : '停用' }}
              </Badge>
            </TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="openEdit(row)">编辑</Button>
                <Button variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="remove(row)">删除</Button>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="7">暂无指标点</TableEmpty>
        </TableBody>
      </Table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>{{ form.id ? '编辑指标点' : '新增指标点' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-3.5">
          <div class="grid gap-1.5">
            <Label>编号 <span class="text-destructive">*</span></Label>
            <Input v-model="form.code" placeholder="例如 1 或 3.2" />
          </div>
          <div class="grid gap-1.5">
            <Label>名称 <span class="text-destructive">*</span></Label>
            <Input v-model="form.name" maxlength="120" placeholder="例如 工程知识" />
          </div>
          <div class="grid gap-1.5">
            <Label>说明</Label>
            <Textarea v-model="form.description" rows="4" maxlength="500" placeholder="指标点详细说明" />
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
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Info, Plus, RefreshCw } from 'lucide-vue-next'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { indicatorApi, statsApi } from '../api'

const router = useRouter()
const items = ref([])
const coverage = ref(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const form = reactive({ id: null, code: '', name: '', description: '', sort_order: 0, is_active: true })

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

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

function validate() {
  if (!form.code.trim()) {
    toast.error('请输入指标点编号')
    return false
  }
  if (!form.name.trim()) {
    toast.error('请输入指标点名称')
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  saving.value = true
  try {
    const payload = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description,
      sort_order: form.sort_order || 0,
      is_active: form.is_active
    }
    if (form.id) {
      await indicatorApi.update(form.id, payload)
      toast.success('指标点已更新')
    } else {
      await indicatorApi.create(payload)
      toast.success('指标点已新增')
    }
    dialogVisible.value = false
    loadAll()
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

function remove(row) {
  askConfirm({
    title: '删除确认',
    description: `删除指标点「${row.code} ${row.name}」将解除 ${row.achievement_count || 0} 条成果的关联，确认继续吗？`,
    confirmText: '删除',
    danger: true,
    handler: async () => {
      await indicatorApi.remove(row.id)
      toast.success('指标点已删除')
      loadAll()
    }
  })
}

function viewAchievements(row) {
  router.push({ path: '/achievements', query: { indicator_id: row.id } })
}

onMounted(loadAll)
</script>