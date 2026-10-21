<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">数据导入导出</h2>
        <p class="page-subtitle">
          通过 Excel 批量导入教师、学生与成果数据；导出成果清单、统计报表、缺件清单与佐证材料包
        </p>
      </div>
      <el-button :icon="Refresh" @click="loadMeta">刷新字典</el-button>
    </div>

    <div class="chart-grid" style="margin-top: 0">
      <div class="card">
        <div class="chart-title">批量导入</div>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="请使用系统提供的模板填写数据，仅支持 .xlsx / .xlsm 格式；导入会自动创建登录账号，可下载模板查看示例行。"
          style="margin-bottom: 16px"
        />

        <el-form :inline="true" label-width="96px" class="import-options">
          <el-form-item label="自动建账号">
            <el-switch v-model="options.createLogin" />
          </el-form-item>
          <el-form-item label="初始密码">
            <el-input v-model="options.defaultPassword" style="width: 140px" />
          </el-form-item>
          <el-form-item label="跳过重复成果">
            <el-switch v-model="options.skipDuplicates" />
          </el-form-item>
        </el-form>

        <div v-for="task in importTasks" :key="task.kind" class="import-block">
          <div class="import-head">
            <div>
              <span class="import-title">{{ task.title }}</span>
              <span class="muted">{{ task.hint }}</span>
            </div>
            <el-button link type="primary" :icon="Download" @click="downloadTemplate(task.kind)">
              下载模板
            </el-button>
          </div>
          <el-upload
            drag
            action="#"
            :show-file-list="false"
            :http-request="(opt) => handleImport(task.kind, opt)"
            accept=".xlsx,.xlsm"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">将 Excel 文件拖到此处，或<em>点击选择文件</em></div>
          </el-upload>
        </div>

        <div v-if="importResult" class="import-result">
          <el-alert :title="importResult.message" :type="importResult.type" show-icon :closable="false" />
          <el-descriptions :column="3" border size="small" style="margin-top: 10px">
            <el-descriptions-item label="成功导入">{{ importResult.created }} 条</el-descriptions-item>
            <el-descriptions-item label="跳过">{{ importResult.skipped }} 条</el-descriptions-item>
            <el-descriptions-item label="其中重复">{{ importResult.duplicates }} 条</el-descriptions-item>
          </el-descriptions>
          <el-table
            v-if="importResult.errors && importResult.errors.length"
            :data="importErrors"
            size="small"
            border
            style="margin-top: 10px"
            max-height="240"
          >
            <el-table-column prop="message" label="逐行提示" />
          </el-table>
        </div>
      </div>

      <div class="card">
        <div class="chart-title">数据导出</div>
        <el-alert
          type="success"
          :closable="false"
          show-icon
          title="报表包含概览、成果明细、类型/年度/级别/院系分布、师生汇总、缺件清单与指标点覆盖等工作表。"
          style="margin-bottom: 16px"
        />

        <el-form :inline="true" style="margin: 0 0 16px">
          <el-form-item label="类型">
            <el-select v-model="exportFilters.category" placeholder="全部" clearable style="width: 140px">
              <el-option v-for="item in allCategories" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="年份">
            <el-select v-model="exportFilters.year" placeholder="全部" clearable style="width: 110px">
              <el-option v-for="item in years" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="人员类型">
            <el-select v-model="exportFilters.owner_type" placeholder="全部" clearable style="width: 110px">
              <el-option label="教师" value="teacher" />
              <el-option label="学生" value="student" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="exportFilters.status" style="width: 120px">
              <el-option label="仅已通过" value="approved" />
              <el-option label="待审核" value="pending" />
              <el-option label="草稿" value="draft" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button text @click="resetFilters">重置筛选</el-button>
          </el-form-item>
        </el-form>

        <div v-for="item in exportTasks" :key="item.key" class="export-item">
          <div>
            <div class="import-title">{{ item.title }}</div>
            <div class="muted">{{ item.hint }}</div>
          </div>
          <el-button
            :type="item.type"
            :icon="item.icon"
            :loading="exporting === item.key"
            @click="item.handler"
          >
            {{ item.action }}
          </el-button>
        </div>

        <el-divider />
        <div class="muted">
          导出文件会自动带上时间戳，便于多次导出对比留档；
          佐证材料包按「院系 / 所属人 / 成果 / 材料分类」组织目录，可直接提交专家查阅。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Files, FolderOpened, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ioApi, metaApi } from '../api'
import { saveBlob } from '../utils/file'

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
  category: '',
  year: '',
  owner_type: '',
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
    type: 'primary',
    icon: Download,
    handler: () => runExport('achievements')
  },
  {
    key: 'report',
    title: '业绩统计报表',
    hint: '概览 + 明细 + 分布 + 师生汇总 + 缺件 + 指标点覆盖，认证材料直接可用',
    action: '导出报表',
    type: 'success',
    icon: Files,
    handler: () => runExport('report')
  },
  {
    key: 'missing',
    title: '缺件清单',
    hint: '列出已通过但尚未归档支撑材料的成果，便于通知师生补充',
    action: '导出缺件',
    type: 'warning',
    icon: Download,
    handler: () => runExport('missing')
  },
  {
    key: 'package',
    title: '佐证材料包（ZIP）',
    hint: '打包成果清单与全部支撑材料文件，按院系与人员自动分目录',
    action: '导出材料包',
    type: 'danger',
    icon: FolderOpened,
    handler: () => runExport('package')
  }
]

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

async function handleImport(kind, uploadOptions) {
  try {
    const file = uploadOptions.file
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
      ElMessage.success(`成功导入 ${data.created} 条数据`)
    } else {
      ElMessage.warning('没有导入任何数据，请检查提示信息')
    }
  } catch (err) {
    importResult.value = buildResult('error', err.message || '导入失败')
    if (uploadOptions.onError) uploadOptions.onError(err)
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
    if (exportFilters[key] !== '' && exportFilters[key] !== null) {
      params[key] = exportFilters[key]
    }
  })
  return params
}

function resetFilters() {
  exportFilters.category = ''
  exportFilters.year = ''
  exportFilters.owner_type = ''
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

<style scoped>
.import-block {
  margin-bottom: 16px;
}

.import-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.import-title {
  font-size: 14px;
  font-weight: 600;
}

.export-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 12px;
}

.import-options {
  margin-bottom: 8px;
}

.muted {
  color: #909399;
  font-size: 12px;
}
</style>