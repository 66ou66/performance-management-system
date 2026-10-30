<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">系统维护</h2>
        <p class="mt-1 text-sm text-muted-foreground">运行状态、数据备份、孤儿附件清理与结构检查</p>
      </div>
      <Button variant="outline" @click="loadAll">
        <RefreshCw class="size-4" /> 刷新
      </Button>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <!-- 运行信息 -->
      <div class="rounded-xl border bg-white p-4 shadow-sm">
        <h4 class="mb-3 text-sm font-semibold">运行信息</h4>
        <dl v-if="info" class="space-y-2.5 text-sm">
          <div class="flex items-center gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">运行模式</dt>
            <dd class="flex items-center gap-2">
              <Badge
                variant="secondary"
                :class="info.app_env === 'production' ? 'text-emerald-600' : 'text-amber-600'"
              >
                {{ info.app_env }}
              </Badge>
              <Badge v-if="info.debug" variant="destructive">调试模式开启</Badge>
            </dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">成果数据</dt>
            <dd>{{ info.coverage.achievements }} 条（回收站 {{ info.coverage.trash }} 条）</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">指标点 / 字典项</dt>
            <dd>{{ info.coverage.indicators }} / {{ info.coverage.dict_items }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">操作日志</dt>
            <dd>{{ info.coverage.logs }} 条</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">支撑材料文件</dt>
            <dd>{{ info.upload_files }} 个（{{ info.upload_size }}）</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">送审模式</dt>
            <dd>{{ info.require_review ? '开启（新成果需审核）' : '关闭（新成果直接通过）' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">强制改密</dt>
            <dd>{{ info.force_password_change ? '开启' : '关闭' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">口令强度校验</dt>
            <dd>{{ info.password_strength_check ? '开启' : '关闭' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">上传上限</dt>
            <dd>{{ info.max_upload_mb }} MB</dd>
          </div>
          <div class="flex gap-2">
            <dt class="w-28 shrink-0 text-muted-foreground">CORS 白名单</dt>
            <dd class="font-mono text-xs">{{ (info.cors_origins || []).join(' , ') }}</dd>
          </div>
        </dl>
      </div>

      <div class="space-y-4">
        <!-- 数据备份 -->
        <div class="rounded-xl border bg-white p-4 shadow-sm">
          <h4 class="mb-1 text-sm font-semibold">数据备份</h4>
          <p class="mb-3 text-xs text-muted-foreground">
            备份包含数据库与 uploads 目录下的全部支撑材料，仅保留最近 {{ backups.keep }} 份。
          </p>
          <Button :disabled="backingUp" @click="createBackup">
            <LoaderCircle v-if="backingUp" class="size-4 animate-spin" />
            <Database v-else class="size-4" />
            立即备份
          </Button>
          <Table class="mt-3">
            <TableHeader>
              <TableRow>
                <TableHead>备份文件</TableHead>
                <TableHead class="w-[90px]">大小</TableHead>
                <TableHead class="w-[160px]">时间</TableHead>
                <TableHead class="w-[90px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="row in backups.items || []" :key="row.name">
                <TableCell class="max-w-[180px] truncate font-medium">{{ row.name }}</TableCell>
                <TableCell>{{ row.size_text }}</TableCell>
                <TableCell class="text-muted-foreground">{{ row.created_at }}</TableCell>
                <TableCell class="text-right">
                  <Button variant="link" size="sm" @click="download(row)">下载</Button>
                </TableCell>
              </TableRow>
              <TableEmpty v-if="!(backups.items || []).length" :colspan="4">暂无备份</TableEmpty>
            </TableBody>
          </Table>
        </div>

        <!-- 数据一致性 -->
        <div class="rounded-xl border bg-white p-4 shadow-sm">
          <h4 class="mb-1 text-sm font-semibold">数据一致性</h4>
          <p class="mb-3 text-xs text-muted-foreground">
            孤儿附件指磁盘上已存在、但没有任何成果引用的文件（例如手工删除成果留下的残留）。
          </p>
          <Alert :class="orphanTotal ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'">
            <AlertDescription :class="orphanTotal ? 'text-amber-700' : 'text-emerald-700'">
              {{ orphanTotal ? `发现 ${orphanTotal} 个孤儿文件` : '未发现孤儿文件' }}
            </AlertDescription>
          </Alert>
          <div class="mt-3 flex flex-wrap gap-2">
            <Button variant="outline" :disabled="loading" @click="loadOrphans">重新扫描</Button>
            <Button variant="destructive" :disabled="!orphanTotal" @click="cleanup">
              <Trash2 class="size-4" /> 清理孤儿文件
            </Button>
            <Button variant="outline" @click="runMigrate">
              <Database class="size-4" /> 检查数据结构
            </Button>
          </div>
          <Table v-if="orphanTotal" class="mt-3">
            <TableHeader>
              <TableRow>
                <TableHead>文件</TableHead>
                <TableHead class="w-[90px]">大小</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, idx) in (orphans.items || []).slice(0, 20)" :key="row.path || idx">
                <TableCell class="max-w-[240px] truncate text-muted-foreground">{{ row.path }}</TableCell>
                <TableCell>{{ row.size_text }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </div>

    <!-- 结构检查记录 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <h4 class="mb-3 text-sm font-semibold">结构检查记录（迁移脚本执行明细）</h4>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[60px]">#</TableHead>
            <TableHead>变更内容</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in migrationRows" :key="row.index">
            <TableCell class="text-muted-foreground">{{ row.index }}</TableCell>
            <TableCell>{{ row.text }}</TableCell>
          </TableRow>
          <TableEmpty v-if="!migrationRows.length" :colspan="2">本次启动未发生结构变更</TableEmpty>
        </TableBody>
      </Table>
    </div>

    <!-- 访问节流状态 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <h4 class="mb-3 text-sm font-semibold">访问节流状态（登录失败锁定）</h4>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[180px]">账号</TableHead>
            <TableHead class="w-[130px]">近期失败次数</TableHead>
            <TableHead class="w-[120px]">状态</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in throttleRows" :key="row.key">
            <TableCell class="font-medium">{{ row.key }}</TableCell>
            <TableCell>{{ row.failures }}</TableCell>
            <TableCell>
              <Badge
                variant="secondary"
                :class="row.locked ? 'text-destructive' : 'text-muted-foreground'"
              >
                {{ row.locked ? '已锁定' : '正常' }}
              </Badge>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!throttleRows.length" :colspan="3">当前没有被锁定的账号</TableEmpty>
        </TableBody>
      </Table>
    </div>

    <!-- 确认弹窗 -->
    <ConfirmDialog
      v-model:open="confirmState.open"
      title="清理确认"
      :description="`确认删除 ${orphanTotal} 个未被引用的文件吗？该操作不会影响任何成果数据。`"
      confirm-text="清理"
      :danger="true"
      @confirm="onConfirm"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Database, LoaderCircle, RefreshCw, Trash2 } from 'lucide-vue-next'
import { systemApi } from '../api'
import { formatSize, saveBlob } from '../utils/file'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const info = ref(null)
const backups = ref({ items: [], keep: 10 })
const orphans = ref({ items: [], total: 0 })
const loading = ref(false)
const backingUp = ref(false)

const confirmState = reactive({
  open: false,
  handler: null
})

const orphanTotal = computed(() => orphans.value.total || 0)
const migrationRows = computed(() => {
  const report = (info.value && info.value.migration_report) || []
  return report.map((text, index) => ({ index: index + 1, text }))
})
const throttleRows = computed(() => {
  const snapshot = (info.value && info.value.login_throttle) || {}
  const accounts = snapshot.accounts || {}
  return Object.entries(accounts).map(([key, value]) => ({
    key,
    failures: value.recent_failures || 0,
    locked: Boolean(value.locked_seconds)
  }))
})

async function loadAll() {
  loading.value = true
  try {
    info.value = await systemApi.info()
    const list = await systemApi.backups()
    backups.value = list
    if (list.items && list.items.length && !orphans.value.total) {
      // 首次进入时顺带扫描一次孤儿文件
      await loadOrphans()
    } else {
      updateOrphanSizes(orphans.value.items || [])
    }
  } catch (err) {
    // 统一错误处理
  } finally {
    loading.value = false
  }
}

function updateOrphanSizes(items) {
  orphans.value.items = items.map((item) => ({ ...item, size_text: formatSize(item.size) }))
}

async function loadOrphans() {
  try {
    const data = await systemApi.orphans()
    orphans.value = { total: data.total, items: data.items || [] }
    updateOrphanSizes(orphans.value.items)
  } catch (err) {
    // 统一错误处理
  }
}

async function createBackup() {
  backingUp.value = true
  try {
    const data = await systemApi.backup()
    toast.success(`备份已生成：${data.name}（${formatSize(data.size)}）`)
    backups.value = await systemApi.backups()
  } catch (err) {
    // 统一错误处理
  } finally {
    backingUp.value = false
  }
}

async function download(row) {
  try {
    const response = await systemApi.downloadBackup(row.name)
    saveBlob(response, row.name)
  } catch (err) {
    // 统一错误处理
  }
}

function cleanup() {
  confirmState.open = true
  confirmState.handler = async () => {
    const data = await systemApi.cleanupOrphans()
    toast.success(`已清理 ${data.removed} 个文件`)
    loadAll()
  }
}

function onConfirm() {
  confirmState.open = false
  const handler = confirmState.handler
  confirmState.handler = null
  if (handler) handler()
}

async function runMigrate() {
  try {
    const data = await systemApi.migrate()
    const actions = data.actions || []
    if (actions.length) {
      toast.success(`执行了 ${actions.length} 项结构变更`)
    } else {
      toast.info('数据结构已是最新，无需变更')
    }
    loadAll()
  } catch (err) {
    // 统一错误处理
  }
}

onMounted(loadAll)
</script>