<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">成果审核</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          教师与学生提交的业绩成果在此集中审核，审核通过后才计入统计与认证材料
        </p>
      </div>
      <div class="flex gap-2">
        <Button variant="outline" @click="loadList"><RefreshCw class="size-4" /> 刷新</Button>
        <Button :disabled="!selectedIds.length" @click="batchApprove">
          批量通过（{{ selectedIds.length }}）
        </Button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">状态</Label>
          <Select v-model="status" @update:model-value="handleSearch">
            <SelectTrigger class="w-[130px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">待审核</SelectItem>
              <SelectItem value="approved">已通过</SelectItem>
              <SelectItem value="rejected">已驳回</SelectItem>
              <SelectItem value="draft">草稿</SelectItem>
              <SelectItem value="__all__">全部</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">关键词</Label>
          <Input v-model="keyword" placeholder="成果名称" class="w-[200px]" @keyup.enter="handleSearch" />
        </div>
        <Button @click="handleSearch"><Search class="size-4" /> 查询</Button>
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
            <TableHead class="w-[115px]">类型</TableHead>
            <TableHead class="w-[100px]">级别</TableHead>
            <TableHead class="w-[80px]">年份</TableHead>
            <TableHead class="w-[90px]">材料</TableHead>
            <TableHead class="w-[165px]">提交时间</TableHead>
            <TableHead class="w-[95px]">状态</TableHead>
            <TableHead>审核意见</TableHead>
            <TableHead class="w-[220px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell>
              <Checkbox :checked="selectedIds.includes(row.id)" @update:checked="toggleSelect(row.id)" />
            </TableCell>
            <TableCell class="max-w-[220px] truncate font-medium">{{ row.title }}</TableCell>
            <TableCell>
              <span>{{ row.owner_name }}</span>
              <Badge variant="secondary" class="ml-1.5 text-muted-foreground">{{ ownerTypeLabel(row.owner_type) }}</Badge>
            </TableCell>
            <TableCell>{{ row.category }}</TableCell>
            <TableCell>{{ row.level || '-' }}</TableCell>
            <TableCell>{{ row.year }}</TableCell>
            <TableCell>
              <Badge v-if="row.attachment_count" variant="secondary" class="text-emerald-600">{{ row.attachment_count }} 份</Badge>
              <Badge v-else variant="secondary" class="text-destructive">缺材料</Badge>
            </TableCell>
            <TableCell class="text-muted-foreground">{{ row.submitted_at }}</TableCell>
            <TableCell>
              <Badge variant="secondary" :class="statusBadgeClass[row.status] || 'text-muted-foreground'">
                {{ statusLabel(row.status) }}
              </Badge>
            </TableCell>
            <TableCell class="max-w-[140px] truncate text-muted-foreground">{{ row.review_comment || '-' }}</TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="openDetail(row)">查看</Button>
                <Button v-if="row.status !== 'approved'" variant="ghost" size="sm" class="text-emerald-600" @click="approve(row)">
                  通过
                </Button>
                <Button v-if="row.status !== 'rejected'" variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="reject(row)">
                  驳回
                </Button>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="11">没有需要处理的成果</TableEmpty>
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
          <DialogTitle>成果审核详情</DialogTitle>
        </DialogHeader>
        <template v-if="detail">
          <dl class="space-y-2.5 text-sm">
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">成果名称</dt><dd class="font-medium">{{ detail.title }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">所属人</dt><dd>{{ detail.owner_name }}（{{ ownerTypeLabel(detail.owner_type) }}）</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">院系</dt><dd>{{ detail.owner_department || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">类型/级别</dt><dd>{{ detail.category }} / {{ detail.level || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">年份/学年</dt><dd>{{ detail.year }} / {{ detail.academic_year || '-' }}</dd></div>
            <div class="flex gap-2">
              <dt class="w-20 shrink-0 text-muted-foreground">支撑材料</dt>
              <dd>
                <div v-if="detail.attachments && detail.attachments.length" class="space-y-1.5">
                  <div v-for="item in detail.attachments" :key="item.id" class="flex items-center gap-2">
                    <Badge variant="secondary">{{ item.category }}</Badge>
                    <span class="truncate">{{ item.original_name }}</span>
                    <Button variant="ghost" size="sm" @click="download(item)">下载</Button>
                  </div>
                </div>
                <span v-else class="text-muted-foreground">暂无支撑材料，建议驳回要求补充</span>
              </dd>
            </div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">成果描述</dt><dd class="whitespace-pre-wrap">{{ detail.description || '暂无' }}</dd></div>
            <div class="flex gap-2"><dt class="w-20 shrink-0 text-muted-foreground">审核意见</dt><dd>{{ detail.review_comment || '暂无' }}</dd></div>
          </dl>
          <div class="mt-3 grid gap-1.5">
            <Label class="text-xs text-muted-foreground">审核意见（驳回时必填）</Label>
            <Textarea v-model="comment" rows="3" placeholder="审核意见（驳回时必填）" />
          </div>
        </template>
        <DialogFooter>
          <Button variant="outline" @click="detailVisible = false">关闭</Button>
          <Button class="bg-emerald-600 hover:bg-emerald-700" @click="approve(detail)">通过</Button>
          <Button variant="destructive" @click="reject(detail)">驳回</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 驳回意见弹窗 -->
    <Dialog v-model:open="rejectDialogVisible">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>驳回成果</DialogTitle>
          <DialogDescription>请填写驳回意见，便于教师/学生修改后重新提交。</DialogDescription>
        </DialogHeader>
        <Textarea v-model="rejectComment" rows="3" placeholder="驳回意见（必填）" />
        <DialogFooter>
          <Button variant="outline" @click="rejectDialogVisible = false">取消</Button>
          <Button variant="destructive" @click="confirmReject">确认驳回</Button>
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
import { RefreshCw, Search } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { achievementApi } from '../api'
import { saveBlob, ownerTypeLabel, statusLabel } from '../utils/file'

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
const status = ref('pending')
const keyword = ref('')
const selectedIds = ref([])
const detailVisible = ref(false)
const detail = ref(null)
const comment = ref('')
const rejectDialogVisible = ref(false)
const rejectRow = ref(null)
const rejectComment = ref('')

const allSelected = computed(() => items.value.length > 0 && selectedIds.value.length === items.value.length)

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (status.value && status.value !== '__all__') params.status = status.value
    if (keyword.value) params.keyword = keyword.value
    const data = await achievementApi.list(params)
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
  comment.value = ''
  detailVisible.value = true
}

async function approve(row) {
  try {
    await achievementApi.review(row.id, 'approve', comment.value || '材料齐全，审核通过')
    toast.success('已通过')
    detailVisible.value = false
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

async function doReject(row, value) {
  await achievementApi.review(row.id, 'reject', value)
  toast.success('已驳回')
  detailVisible.value = false
  loadList()
}

function reject(row) {
  const prefill = detail.value && row.id === detail.value.id ? comment.value.trim() : ''
  if (prefill) {
    doReject(row, prefill)
    return
  }
  rejectRow.value = row
  rejectComment.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  const value = rejectComment.value.trim()
  if (!value) {
    toast.error('驳回意见不能为空')
    return
  }
  rejectDialogVisible.value = false
  await doReject(rejectRow.value, value)
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

async function batchApprove() {
  const ids = selectedIds.value
  askConfirm({
    title: '批量审核',
    description: `确认通过所选 ${ids.length} 条成果吗？`,
    confirmText: '全部通过',
    danger: false,
    handler: async () => {
      const data = await achievementApi.batch('set_status', { ids, status: 'approved' })
      toast.success(`已处理 ${data.affected} 条`)
      selectedIds.value = []
      loadList()
    }
  })
}

async function download(row) {
  try {
    const response = await achievementApi.downloadAttachment(detail.value.id, row.id, false)
    saveBlob(response, row.original_name)
  } catch (err) {
    // 统一错误处理
  }
}

onMounted(loadList)
</script>