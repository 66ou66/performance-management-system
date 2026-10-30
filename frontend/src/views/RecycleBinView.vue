<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">回收站</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          删除的成果会先进入回收站，支撑材料一并保留，可随时恢复或彻底删除
        </p>
      </div>
      <div class="flex gap-2">
        <Button :disabled="!selectedIds.length" @click="batchRestore">
          批量恢复（{{ selectedIds.length }}）
        </Button>
        <Button
          v-if="isAdmin"
          variant="destructive"
          :disabled="!selectedIds.length"
          @click="batchPurge"
        >
          批量彻底删除
        </Button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">关键词</Label>
          <Input
            v-model="keyword"
            placeholder="成果名称"
            class="w-[200px]"
            @keyup.enter="handleSearch"
          />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">类型</Label>
          <Select v-model="category" @update:model-value="handleSearch">
            <SelectTrigger class="w-[140px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in categories" :key="item" :value="item">{{ item }}</SelectItem>
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
            <TableHead class="w-[44px]">
              <Checkbox :checked="allSelected" @update:checked="toggleAll" />
            </TableHead>
            <TableHead>成果名称</TableHead>
            <TableHead class="w-[140px]">所属人</TableHead>
            <TableHead class="w-[120px]">类型</TableHead>
            <TableHead class="w-[80px]">年份</TableHead>
            <TableHead class="w-[90px]">材料</TableHead>
            <TableHead class="w-[170px]">删除时间</TableHead>
            <TableHead class="w-[200px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell>
              <Checkbox :checked="selectedIds.includes(row.id)" @update:checked="toggleSelect(row.id)" />
            </TableCell>
            <TableCell class="max-w-[240px] truncate font-medium">{{ row.title }}</TableCell>
            <TableCell>
              <span>{{ row.owner_name }}</span>
              <Badge variant="secondary" class="ml-1.5 text-muted-foreground">{{ ownerTypeLabel(row.owner_type) }}</Badge>
            </TableCell>
            <TableCell>{{ row.category }}</TableCell>
            <TableCell>{{ row.year }}</TableCell>
            <TableCell>{{ row.attachment_count || 0 }} 份</TableCell>
            <TableCell class="text-muted-foreground">{{ row.deleted_at || '-' }}</TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="restore(row)">恢复</Button>
                <Button variant="ghost" size="sm" @click="openDetail(row)">查看</Button>
                <Button v-if="isAdmin" variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="purge(row)">
                  彻底删除
                </Button>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="8">回收站为空</TableEmpty>
        </TableBody>
      </Table>

      <div class="border-t px-4 py-3">
        <AppPagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <Dialog v-model:open="detailVisible">
      <DialogContent class="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>已删除成果详情</DialogTitle>
        </DialogHeader>
        <dl v-if="detail" class="space-y-3 text-sm">
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">成果名称</dt><dd class="font-medium">{{ detail.title }}</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">所属人</dt><dd>{{ detail.owner_name }}（{{ ownerTypeLabel(detail.owner_type) }}）</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">类型 / 级别</dt><dd>{{ detail.category }} / {{ detail.level || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">年份</dt><dd>{{ detail.year }}</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">删除时间</dt><dd>{{ detail.deleted_at || '-' }}</dd></div>
          <div class="flex gap-2">
            <dt class="w-24 shrink-0 text-muted-foreground">支撑材料</dt>
            <dd>
              <div v-if="detail.attachments && detail.attachments.length">
                <div v-for="item in detail.attachments" :key="item.id" class="text-muted-foreground">
                  {{ item.category }}：{{ item.original_name }}
                </div>
              </div>
              <span v-else class="text-muted-foreground">无</span>
            </dd>
          </div>
        </dl>
        <DialogFooter>
          <Button variant="outline" @click="detailVisible = false">关闭</Button>
          <Button @click="restore(detail)">恢复该成果</Button>
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
import { RotateCcw, Search } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { achievementApi, metaApi } from '../api'
import { useUserStore } from '../stores/user'
import { ownerTypeLabel } from '../utils/file'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const keyword = ref('')
const category = ref('__all__')
const categories = ref([])
const selectedIds = ref([])
const detail = ref(null)
const detailVisible = ref(false)

const allSelected = computed(() => items.value.length > 0 && selectedIds.value.length === items.value.length)

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

async function loadMeta() {
  try {
    const data = await metaApi.options()
    categories.value = data.all_categories || []
  } catch (err) {
    categories.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (category.value && category.value !== '__all__') params.category = category.value
    const data = await achievementApi.trash(params)
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
  keyword.value = ''
  category.value = '__all__'
  page.value = 1
  loadList()
}

function toggleSelect(id) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}

function toggleAll() {
  if (allSelected.value) selectedIds.value = []
  else selectedIds.value = items.value.map((row) => row.id)
}

function openDetail(row) {
  detail.value = row
  detailVisible.value = true
}

async function restore(row) {
  if (!row) return
  try {
    await achievementApi.restore(row.id)
    toast.success('成果已恢复')
    detailVisible.value = false
    selectedIds.value = selectedIds.value.filter((id) => id !== row.id)
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

function purge(row) {
  askConfirm({
    title: '彻底删除',
    description: `彻底删除后「${row.title}」及其支撑材料将无法恢复，确认继续吗？`,
    confirmText: '彻底删除',
    danger: true,
    handler: async () => {
      await achievementApi.remove(row.id, true)
      toast.success('已彻底删除')
      loadList()
    }
  })
}

async function batchRestore() {
  const ids = selectedIds.value
  try {
    const data = await achievementApi.batch('restore', { ids })
    toast.success(`已恢复 ${data.affected} 条`)
    selectedIds.value = []
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function batchPurge() {
  const ids = selectedIds.value
  askConfirm({
    title: '彻底删除',
    description: `确认彻底删除所选 ${ids.length} 条成果及其材料吗？`,
    confirmText: '彻底删除',
    danger: true,
    handler: async () => {
      const data = await achievementApi.batch('purge', { ids })
      toast.success(`已彻底删除 ${data.affected} 条`)
      selectedIds.value = []
      loadList()
    }
  })
}

onMounted(() => {
  loadMeta()
  loadList()
})
</script>