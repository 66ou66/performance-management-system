<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">数据导入导出</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          通过 Excel 批量导入教师、学生与成果数据；导出成果清单、统计报表、缺件清单与佐证材料包
        </p>
      </div>
      <Button variant="outline" @click="loadMeta">
        <RefreshCw class="size-4" /> 刷新字典
      </Button>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <!-- 批量导入 -->
      <div class="rounded-xl border bg-white p-4 shadow-sm">
        <h3 class="mb-3 text-base font-semibold">批量导入</h3>

        <Alert class="mb-4">
          <Info class="size-4" />
          <AlertDescription>
            请使用系统提供的模板填写数据，仅支持 .xlsx / .xlsm 格式；导入会自动创建登录账号，可下载模板查看示例行。
          </AlertDescription>
        </Alert>

        <div class="mb-4 flex flex-wrap items-center gap-x-5 gap-y-3">
          <div class="flex items-center gap-2">
            <Switch :checked="options.createLogin" @update:checked="options.createLogin = $event" />
            <Label class="text-sm text-muted-foreground">自动建账号</Label>
          </div>
          <div class="flex items-center gap-2">
            <Label class="text-sm text-muted-foreground">初始密码</Label>
            <Input v-model="options.defaultPassword" class="w-[120px]" />
          </div>
          <div class="flex items-center gap-2">
            <Switch :checked="options.skipDuplicates" @update:checked="options.skipDuplicates = $event" />
            <Label class="text-sm text-muted-foreground">跳过重复成果</Label>
          </div>
        </div>

        <div v-for="task in importTasks" :key="task.kind" class="mb-4 last:mb-0">
          <div class="mb-2 flex items-center justify-between gap-3">
            <div>
              <span class="text-sm font-semibold">{{ task.title }}</span>
              <span class="ml-1.5 text-xs text-muted-foreground">{{ task.hint }}</span>
            </div>
            <Button variant="link" size="sm" @click="downloadTemplate(task.kind)">
              <Download class="size-4" /> 下载模板
            </Button>
          </div>
          <label
            class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-input p-6 text-center transition-colors hover:border-primary/50 hover:bg-accent/40"
          >
            <Upload class="size-6 text-muted-foreground" />
            <div class="text-sm text-muted-foreground">点击选择 Excel 文件（.xlsx / .xlsm）</div>
            <input
              type="file"
              accept=".xlsx,.xlsm"
              class="hidden"
              @change="onFileSelect($event, task.kind)"
            />
          </label>
        </div>

        <div v-if="importResult" class="mt-4 space-y-3">
          <Alert :variant="importResult.type === 'error' ? 'destructive' : 'default'" :class="resultAlertClass">
            <AlertDescription>{{ importResult.message }}</AlertDescription>
          </Alert>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="rounded-md border bg-muted/40 p-2">
              <div class="text-base font-semibold">{{ importResult.created }}</div>
              <div class="text-xs text-muted-foreground">成功导入</div>
            </div>
            <div class="rounded-md border bg-muted/40 p-2">
              <div class="text-base font-semibold">{{ importResult.skipped }}</div>
              <div class="text-xs text-muted-foreground">跳过</div>
            </div>
            <div class="rounded-md border bg-muted/40 p-2">
              <div class="text-base font-semibold">{{ importResult.duplicates }}</div>
              <div class="text-xs text-muted-foreground">其中重复</div>
            </div>
          </div>
          <Table v-if="importErrors.length">
            <TableHeader>
              <TableRow>
                <TableHead>逐行提示</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(item, idx) in importErrors" :key="idx">
                <TableCell class="text-muted-foreground">{{ item.message }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>

      <!-- 数据导出 -->
      <div class="rounded-xl border bg-white p-4 shadow-sm">
        <h3 class="mb-3 text-base font-semibold">数据导出</h3>

        <Alert class="mb-4 border-emerald-200 bg-emerald-50">
          <AlertDescription class="text-emerald-700">
            报表包含概览、成果明细、类型/年度/级别/院系分布、师生汇总、缺件清单与指标点覆盖等工作表。
          </AlertDescription>
        </Alert>

        <div class="mb-4 flex flex-wrap items-end gap-3">
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">类型</Label>
            <Select v-model="exportFilters.category">
              <SelectTrigger class="w-[140px]"><SelectValue placeholder="全部" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                <SelectItem v-for="item in allCategories" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">年份</Label>
            <Select v-model="exportFilters.year">
              <SelectTrigger class="w-[110px]"><SelectValue placeholder="全部" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                <SelectItem v-for="item in years" :key="item" :value="String(item)">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">人员类型</Label>
            <Select v-model="exportFilters.owner_type">
              <SelectTrigger class="w-[110px]"><SelectValue placeholder="全部" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                <SelectItem value="teacher">教师</SelectItem>
                <SelectItem value="student">学生</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-1.5">
            <Label class="text-xs text-muted-foreground">状态</Label>
            <Select v-model="exportFilters.status">
              <SelectTrigger class="w-[120px]"><SelectValue placeholder="状态" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="approved">仅已通过</SelectItem>
                <SelectItem value="pending">待审核</SelectItem>
                <SelectItem value="draft">草稿</SelectItem>
                <SelectItem value="rejected">已驳回</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="ghost" size="sm" @click="resetFilters">
            <RotateCcw class="size-4" /> 重置筛选
          </Button>
        </div>

        <div
          v-for="item in exportTasks"
          :key="item.key"
          class="mb-3 flex items-center justify-between gap-4 rounded-lg bg-muted/40 p-3"
        >
          <div>
            <div class="text-sm font-semibold">{{ item.title }}</div>
            <div class="text-xs text-muted-foreground">{{ item.hint }}</div>
          </div>
          <Button
            :variant="item.variant"
            :class="exportToneClass[item.tone]"
            :disabled="exporting === item.key"
            @click="item.handler"
          >
            <LoaderCircle v-if="exporting === item.key" class="size-4 animate-spin" />
            <component :is="item.icon" v-else class="size-4" />
            {{ item.action }}
          </Button>
        </div>

        <Separator class="my-4" />
        <p class="text-xs text-muted-foreground">
          导出文件会自动带上时间戳，便于多次导出对比留档；佐证材料包按「院系 / 所属人 / 成果 / 材料分类」组织目录，可直接提交专家查阅。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'
import {
  BarChart3,
  Download,
  FileArchive,
  FileSpreadsheet,
  Info,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Upload
} from 'lucide-vue-next'
import { ioApi, metaApi } from '../api'
import { saveBlob } from '../utils/file'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const allCategories = ref([])
const years = ref([])
const importResult = ref(null)
const exporting = ref('')

const options = reactive({
  createLogin: true,
  defaultPassword: '123456',
  skipDuplicates: true
})

const exportFilters = reactive({
  category: '__all__',
  year: '__all__',
  owner_type: '__all__',
  status: 'approved'
})

const importTasks = [
  {
    kind: 'teachers',
    title: '教师信息导入',
    hint: '（姓名、院系、职称、联系方式，可同时创建登录账号）'
  },
  {
    kind: 'students',
    title: '学生信息导入',
    hint: '（学号、姓名、年级、专业、班级，可绑定指导教师）'
  },
  {
    kind: 'achievements',
    title: '业绩成果导入',
    hint: '（按成果类别分表填写，含类别专有字段）'
  }
]

const exportTasks = [
  {
    key: 'achievements',
    title: '业绩成果清单',
    hint: '按当前筛选条件导出成果明细，含专有字段、指标点与材料清单',
    action: '导出清单',
    variant: 'default',
    tone: '',
    icon: FileSpreadsheet,
    handler: () => runExport('achievements')
  },
  {
    key: 'report',
    title: '业绩统计报表',
    hint: '概览 + 明细 + 分布 + 师生汇总 + 缺件 + 指标点覆盖，认证材料直接可用',
    action: '导出报表',
    variant: 'default',
    tone: 'emerald',
    icon: BarChart3,
    handler: () => runExport('report')
  },
  {
    key: 'missing',
    title: '缺件清单',
    hint: '列出已通过但尚未归档支撑材料的成果，便于通知师生补充',
    action: '导出缺件',
    variant: 'default',
    tone: 'amber',
    icon: Download,
    handler: () => runExport('missing')
  },
  {
    key: 'package',
    title: '佐证材料包（ZIP）',
    hint: '打包成果清单与全部支撑材料文件，按院系与人员自动分目录',
    action: '导出材料包',
    variant: 'destructive',
    tone: '',
    icon: FileArchive,
    handler: () => runExport('package')
  }
]

const exportToneClass = {
  '': '',
  emerald: 'bg-emerald-600 text-white hover:bg-emerald-600/90',
  amber: 'bg-amber-500 text-white hover:bg-amber-500/90'
}

const resultAlertClass = computed(() => {
  const type = importResult.value && importResult.value.type
  if (type === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (type === 'warning') return 'border-amber-200 bg-amber-50 text-amber-700'
  return ''
})

const importErrors = computed(() =>
  (importResult.value?.errors || []).map((message) => ({ message }))
)

async function loadMeta() {
  try {
    const data = await metaApi.options()
    allCategories.value = data.all_categories || []
    years.value = data.years || []
  } catch (err) {
    // 统一错误处理
  }
}

function buildResult(type, message, data) {
  return {
    type,
    message,
    created: (data && data.created) || 0,
    skipped: (data && data.skipped) || 0,
    duplicates: (data && data.duplicates) || 0,
    errors: (data && data.errors) || []
  }
}

function importOptions() {
  return {
    create_login: options.createLogin ? '1' : '0',
    default_password: options.defaultPassword,
    skip_duplicates: options.skipDuplicates ? '1' : '0'
  }
}

function onFileSelect(event, kind) {
  const file = event.target.files && event.target.files[0]
  event.target.value = ''
  if (file) handleImport(kind, file)
}

async function handleImport(kind, file) {
  try {
    const extra = importOptions()
    let data
    if (kind === 'teachers') {
      data = await ioApi.importTeachers(file, extra)
    } else if (kind === 'students') {
      data = await ioApi.importStudents(file, extra)
    } else {
      data = await ioApi.importAchievements(file, extra)
    }
    importResult.value = buildResult(
      data.created ? 'success' : 'warning',
      `导入完成：成功 ${data.created} 条，跳过 ${data.skipped} 条`,
      data
    )
    if (data.created) {
      toast.success(`成功导入 ${data.created} 条数据`)
    } else {
      toast.warning('没有导入任何数据，请检查提示信息')
    }
  } catch (err) {
    importResult.value = buildResult('error', err.message || '导入失败')
  }
}

async function downloadTemplate(kind) {
  try {
    let response
    let name
    if (kind === 'teachers') {
      response = await ioApi.teacherTemplate()
      name = '教师信息导入模板.xlsx'
    } else if (kind === 'students') {
      response = await ioApi.studentTemplate()
      name = '学生信息导入模板.xlsx'
    } else {
      response = await ioApi.achievementTemplate()
      name = '成果信息导入模板.xlsx'
    }
    saveBlob(response, name)
  } catch (err) {
    // 统一错误处理
  }
}

function filterParams() {
  const params = {}
  Object.keys(exportFilters).forEach((key) => {
    const value = exportFilters[key]
    if (value !== '' && value !== null && value !== '__all__') {
      params[key] = value
    }
  })
  return params
}

function resetFilters() {
  exportFilters.category = '__all__'
  exportFilters.year = '__all__'
  exportFilters.owner_type = '__all__'
  exportFilters.status = 'approved'
}

async function runExport(kind) {
  exporting.value = kind
  const params = filterParams()
  try {
    if (kind === 'achievements') {
      saveBlob(await ioApi.exportAchievements(params), '业绩成果清单.xlsx')
    } else if (kind === 'report') {
      saveBlob(await ioApi.exportReport(params), '专业业绩统计报表.xlsx')
    } else if (kind === 'missing') {
      saveBlob(
        await ioApi.exportMissingEvidence({ ...params, has_attachment: '0' }),
        '缺件清单.xlsx'
      )
    } else {
      saveBlob(await ioApi.exportPackage(params), '佐证材料包.zip')
    }
  } catch (err) {
    // 统一错误处理
  } finally {
    exporting.value = ''
  }
}

onMounted(loadMeta)
</script>