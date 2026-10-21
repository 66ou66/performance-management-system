<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">业绩成果管理</h2>
        <p class="page-subtitle">
          教师教学/科研/指导学生成果与学生竞赛、论文、专利、软著等业绩的录入与多条件检索
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Delete" @click="$router.push('/trash')">回收站</el-button>
        <el-button :icon="Download" @click="handleExport">导出当前结果</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增成果</el-button>
      </div>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="成果名称/描述/级别"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="所属人">
          <el-input
            v-model="filters.owner_name"
            placeholder="姓名"
            clearable
            style="width: 110px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filters.category" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="item in allCategories" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="filters.level" placeholder="全部" clearable filterable style="width: 120px">
            <el-option v-for="item in levelOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="年份">
          <el-select v-model="filters.year" placeholder="全部" clearable style="width: 100px">
            <el-option v-for="item in years" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="学年">
          <el-select v-model="filters.academic_year" placeholder="全部" clearable style="width: 120px">
            <el-option v-for="item in academicYears" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isElevated" label="人员类型">
          <el-select v-model="filters.owner_type" placeholder="全部" clearable style="width: 100px">
            <el-option label="教师" value="teacher" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="院系">
          <el-select
            v-model="filters.department"
            placeholder="全部"
            clearable
            filterable
            allow-create
            style="width: 140px"
          >
            <el-option v-for="item in departments" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 110px">
            <el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="材料">
          <el-select v-model="filters.has_attachment" placeholder="全部" clearable style="width: 110px">
            <el-option label="已归档" value="1" />
            <el-option label="缺材料" value="0" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isElevated" label="指标点">
          <el-select v-model="filters.indicator_id" placeholder="全部" clearable filterable style="width: 160px">
            <el-option
              v-for="item in indicators"
              :key="item.id"
              :label="`${item.code} ${item.name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div v-if="selection.length" class="batch-bar">
        <span>已选择 {{ selection.length }} 条</span>
        <el-button size="small" @click="batchSetLevel">批量设级别</el-button>
        <el-button size="small" @click="batchAddIndicators">批量关联指标点</el-button>
        <el-button v-if="isElevated" size="small" @click="batchSetStatus">批量改状态</el-button>
        <el-button size="small" type="danger" plain @click="batchDelete">批量移入回收站</el-button>
        <el-button size="small" text @click="selection = []">取消选择</el-button>
      </div>

      <el-table
        :data="items"
        v-loading="loading"
        border
        stripe
        empty-text="暂无成果数据"
        @selection-change="(rows) => (selection = rows)"
        @sort-change="handleSortChange"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column prop="title" label="成果名称" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.title }}</span>
            <el-tag
              v-if="!row.attachment_count"
              size="small"
              type="danger"
              effect="plain"
              style="margin-left: 6px"
            >
              缺材料
            </el-tag>
            <el-tag
              v-else
              size="small"
              type="success"
              effect="plain"
              style="margin-left: 6px"
            >
              {{ row.attachment_count }} 份材料
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="所属人" width="150" sortable="custom" prop="owner_name">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="filterByOwner(row.owner_name)">
              {{ row.owner_name }}
            </el-link>
            <el-tag size="small" effect="plain" type="info">
              {{ ownerTypeLabel(row.owner_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner_department" label="院系" width="130" show-overflow-tooltip />
        <el-table-column prop="category" label="成果类型" width="115" sortable="custom" />
        <el-table-column prop="level" label="级别" width="110" sortable="custom">
          <template #default="{ row }">
            <el-tag v-if="row.level" size="small" :type="levelTagType(row.level)">{{ row.level }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="year" label="年份" width="90" sortable="custom" />
        <el-table-column prop="status" label="状态" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagTypes[row.status] || 'info'">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="指标点" width="120">
          <template #default="{ row }">
            <span v-if="row.indicators && row.indicators.length">
              {{ row.indicators.map((item) => item.code).join('、') }}
            </span>
            <span v-else class="muted">未关联</span>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="165" sortable="custom" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
            <el-button v-if="canEditRow(row)" link type="primary" size="small" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button link type="primary" size="small" @click="openAttachments(row)">
              材料
            </el-button>
            <el-dropdown trigger="click" @command="(command) => handleRowCommand(command, row)">
              <el-button link type="primary" size="small">
                更多<el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="submit" :disabled="row.status === 'approved'">
                    提交审核
                  </el-dropdown-item>
                  <el-dropdown-item v-if="isElevated" command="approve">
                    审核通过
                  </el-dropdown-item>
                  <el-dropdown-item v-if="isElevated" command="reject">审核驳回</el-dropdown-item>
                  <el-dropdown-item v-if="canEditRow(row)" command="indicators">
                    关联指标点
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canEditRow(row)" command="delete" divided>
                    移入回收站
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="loadList"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- 新增 / 编辑 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增业绩成果' : '编辑业绩成果'"
      width="680px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="104px">
        <el-form-item v-if="isAdmin" label="人员类型" prop="owner_type">
          <el-radio-group v-model="form.owner_type" @change="handleOwnerTypeChange">
            <el-radio-button value="teacher">教师</el-radio-button>
            <el-radio-button value="student">学生</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="isAdmin" label="所属人" prop="owner_id">
          <el-select v-model="form.owner_id" filterable placeholder="请选择所属人" style="width: 100%">
            <el-option v-for="item in ownerOptions" :key="item.id" :label="item.label" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="所属人">
          <el-input :model-value="userStore.displayName" disabled />
        </el-form-item>
        <el-form-item label="成果类型" prop="category">
          <el-select v-model="form.category" placeholder="请选择成果类型" style="width: 100%">
            <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="成果名称" prop="title">
          <el-input v-model="form.title" maxlength="255" show-word-limit placeholder="请输入成果名称" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="年份" prop="year">
              <el-select v-model="form.year" style="width: 100%" @change="handleYearChange">
                <el-option v-for="item in yearOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学年">
              <el-input v-model="form.academic_year" placeholder="如 2024-2025" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="级别">
              <el-select v-model="form.level" placeholder="请选择级别" clearable style="width: 100%">
                <el-option v-for="item in formLevels" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="完成人排序">
              <el-select v-model="form.role_rank" placeholder="请选择" clearable style="width: 100%">
                <el-option v-for="item in roleRanks" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="canPickAdvisor" label="指导教师">
          <el-select v-model="form.advisor_id" placeholder="请选择指导教师" clearable filterable style="width: 100%">
            <el-option
              v-for="item in advisorOptions"
              :key="item.id"
              :label="`${item.name}（${item.department || '未设院系'}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-divider v-if="formFields.length" content-position="left">
          {{ form.category }}专有字段
        </el-divider>
        <el-row v-if="formFields.length" :gutter="12">
          <el-col v-for="field in formFields" :key="field.key" :span="field.type === 'textarea' ? 24 : 12">
            <el-form-item :label="field.label">
              <el-select
                v-if="field.type === 'select'"
                v-model="form.extra[field.key]"
                clearable
                style="width: 100%"
              >
                <el-option v-for="item in field.options || []" :key="item" :label="item" :value="item" />
              </el-select>
              <el-input-number
                v-else-if="field.type === 'number'"
                v-model="form.extra[field.key]"
                :controls="false"
                style="width: 100%"
              />
              <el-date-picker
                v-else-if="field.type === 'date'"
                v-model="form.extra[field.key]"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                style="width: 100%"
              />
              <el-input
                v-else
                v-model="form.extra[field.key]"
                :maxlength="field.maxlength || 200"
                :type="field.type === 'textarea' ? 'textarea' : 'text'"
                :rows="2"
                :placeholder="`请输入${field.label}`"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="认证指标点">
          <el-select
            v-model="form.indicator_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="可关联工程教育认证毕业要求指标点"
            style="width: 100%"
          >
            <el-option
              v-for="item in indicators"
              :key="item.id"
              :label="`${item.code} ${item.name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="成果描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="请填写成果的简要说明"
          />
        </el-form-item>
        <el-form-item v-if="isElevated" label="审核状态">
          <el-select v-model="form.status" clearable style="width: 100%">
            <el-option v-for="item in statuses" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 支撑材料 -->
    <el-dialog v-model="attachmentVisible" title="支撑材料管理" width="720px">
      <template v-if="currentRow">
        <p class="dialog-hint">
          成果：<strong>{{ currentRow.title }}</strong>（{{ currentRow.category }}）
          —— 共 {{ currentRow.attachment_count || 0 }} 份材料
        </p>
        <div v-if="canEditRow(currentRow)" class="upload-row">
          <el-select v-model="uploadCategory" style="width: 180px">
            <el-option v-for="item in attachmentCategories" :key="item" :label="item" :value="item" />
          </el-select>
          <el-upload
            action="#"
            multiple
            :show-file-list="false"
            :http-request="handleUploadRequest"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.gif,.bmp,.webp,.zip,.rar,.7z"
          >
            <el-button type="primary" :icon="Upload">上传材料</el-button>
          </el-upload>
          <span class="muted">单条成果最多 20 份，单个文件不超过 20MB</span>
        </div>
        <p v-else class="dialog-hint muted">当前角色仅可查看与下载支撑材料。</p>
        <el-table :data="currentRow.attachments || []" border size="small" empty-text="暂无支撑材料">
          <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column prop="category" label="材料分类" width="140" />
          <el-table-column prop="size_text" label="大小" width="90" />
          <el-table-column prop="uploaded_at" label="上传时间" width="160" />
          <el-table-column label="操作" :width="canEditRow(currentRow) ? 150 : 110">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="downloadAttachment(row, false)">
                下载
              </el-button>
              <el-button link type="primary" size="small" @click="downloadAttachment(row, true)">
                预览
              </el-button>
              <el-button v-if="canEditRow(currentRow)" link type="danger" size="small"
                         @click="removeAttachment(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-drawer v-model="drawerVisible" title="成果详情" size="520px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="成果名称">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="审核状态">
            <el-tag size="small" :type="statusTagTypes[detail.status] || 'info'">
              {{ statusLabel(detail.status) }}
            </el-tag>
            <span v-if="detail.review_comment" class="muted">（{{ detail.review_comment }}）</span>
          </el-descriptions-item>
          <el-descriptions-item label="所属人">
            {{ detail.owner_name }}（{{ ownerTypeLabel(detail.owner_type) }}）
          </el-descriptions-item>
          <el-descriptions-item label="所属院系">{{ detail.owner_department || '-' }}</el-descriptions-item>
          <el-descriptions-item label="成果类型">{{ detail.category }}</el-descriptions-item>
          <el-descriptions-item label="级别">{{ detail.level || '-' }}</el-descriptions-item>
          <el-descriptions-item label="年份 / 学年">
            {{ detail.year || '-' }} / {{ detail.academic_year || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="完成人排序">{{ detail.role_rank || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.advisor_name" label="指导教师">
            {{ detail.advisor_name }}
          </el-descriptions-item>
          <el-descriptions-item label="认证指标点">
            <template v-if="detail.indicators && detail.indicators.length">
              <el-tag
                v-for="item in detail.indicators"
                :key="item.id"
                size="small"
                effect="plain"
                style="margin-right: 6px"
              >
                {{ item.code }} {{ item.name }}
              </el-tag>
            </template>
            <span v-else class="muted">未关联</span>
          </el-descriptions-item>
          <el-descriptions-item label="支撑材料">
            <template v-if="detail.attachments && detail.attachments.length">
              <div v-for="item in detail.attachments" :key="item.id" class="attachment-line">
                <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                <span class="attachment-name">{{ item.original_name }}</span>
                <el-button link type="primary" size="small" @click="downloadAttachment(item, true)">
                  预览
                </el-button>
                <el-button link type="primary" size="small" @click="downloadAttachment(item, false)">
                  下载
                </el-button>
              </div>
            </template>
            <span v-else class="muted">暂无支撑材料</span>
          </el-descriptions-item>
          <el-descriptions-item label="专有字段">
            <div v-if="extraEntries(detail).length">
              <div v-for="entry in extraEntries(detail)" :key="entry.label">
                {{ entry.label }}：{{ entry.value }}
              </div>
            </div>
            <span v-else class="muted">暂无</span>
          </el-descriptions-item>
          <el-descriptions-item label="成果描述">
            <div style="white-space: pre-wrap">{{ detail.description || '暂无描述' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="录入 / 更新">
            {{ detail.created_at }} / {{ detail.updated_at }}
          </el-descriptions-item>
        </el-descriptions>
        <div class="drawer-actions">
          <el-button v-if="canEditRow(detail)" type="primary" @click="openEdit(detail)">编辑</el-button>
          <el-button @click="openAttachments(detail)">
            {{ canEditRow(detail) ? '管理支撑材料' : '查看支撑材料' }}
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Delete, Download, Plus, RefreshLeft, Search, Upload } from '@element-plus/icons-vue'
import { achievementApi, ioApi, metaApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'
import {
  academicYearOf,
  openBlob,
  ownerTypeLabel,
  saveBlob,
  statusLabel,
  statusTagTypes
} from '../utils/file'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')
const isElevated = computed(() => userStore.isElevated)
// 与后端 `_can_edit` 对齐：管理员可改全部，其他角色只能改本人成果
// （教师/学生的列表本身已按本人范围过滤，审核员仅可查看与审核）
const canEditRow = (row) => {
  if (!row) return false
  if (isAdmin.value) return true
  if (isElevated.value) return false
  return row.owner_type === userStore.role
}

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const saving = ref(false)
const selection = ref([])
const sort = ref({ prop: '-year', order: null })

const allCategories = ref([])
const teacherCategories = ref([])
const studentCategories = ref([])
const levelsByCategory = ref({})
const levels = ref([])
const levelOptions = computed(() => (filters.category ? formLevels.value : levels.value))
const years = ref([])
const academicYears = ref([])
const departments = ref([])
const indicators = ref([])
const fieldTemplates = ref({})
const awardRanks = ref([])
const roleRanks = ref([])
const statuses = ref([])
const attachmentCategories = ref([])

const filters = reactive({
  keyword: '',
  owner_name: '',
  category: '',
  level: '',
  year: '',
  academic_year: '',
  owner_type: '',
  department: '',
  status: '',
  has_attachment: '',
  indicator_id: ''
})

const dialogVisible = ref(false)
const dialogMode = ref('create')
const formRef = ref(null)
const ownerOptions = ref([])
const advisorOptions = ref([])
const drawerVisible = ref(false)
const detail = ref(null)

const attachmentVisible = ref(false)
const currentRow = ref(null)
const uploadCategory = ref('其他')

function emptyForm() {
  return {
    id: null,
    owner_type: isAdmin.value ? 'teacher' : userStore.role,
    owner_id: null,
    category: '',
    title: '',
    year: new Date().getFullYear(),
    academic_year: academicYearOf(new Date().getFullYear()),
    level: '',
    role_rank: '',
    advisor_id: null,
    indicator_ids: [],
    extra: {},
    description: '',
    status: ''
  }
}

const form = reactive(emptyForm())
const yearOptions = computed(() => {
  const current = new Date().getFullYear() + 1
  const list = []
  for (let year = current; year >= 1990; year -= 1) list.push(year)
  return list
})

const formRules = {
  owner_type: [{ required: true, message: '请选择人员类型', trigger: 'change' }],
  owner_id: [{ required: true, message: '请选择所属人', trigger: 'change' }],
  category: [{ required: true, message: '请选择成果类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入成果名称', trigger: 'blur' }],
  year: [{ required: true, message: '请选择年份', trigger: 'change' }]
}

const categoryOptions = computed(() => {
  if (form.owner_type === 'teacher') return teacherCategories.value
  if (form.owner_type === 'student') return studentCategories.value
  return allCategories.value
})

const formLevels = computed(() => {
  if (!form.category) return levels.value
  return levelsByCategory.value[form.category] || levels.value
})

const formFields = computed(() => fieldTemplates.value[form.category] || [])

const canPickAdvisor = computed(() => {
  const ownerType = isAdmin.value ? form.owner_type : userStore.role
  return ownerType === 'student'
})

function levelTagType(level) {
  const mapping = {
    国家级: 'danger',
    国际级: 'danger',
    省部级: 'warning',
    省级: 'warning',
    市厅级: 'primary',
    校级: 'success',
    院级: 'info',
    其他: 'info'
  }
  return mapping[level] || 'info'
}

async function loadMeta() {
  try {
    const data = await metaApi.options()
    allCategories.value = data.all_categories || []
    teacherCategories.value = data.teacher_categories || []
    studentCategories.value = data.student_categories || []
    levels.value = data.levels || []
    levelsByCategory.value = data.levels_by_category || {}
    years.value = data.years || []
    academicYears.value = data.academic_years || []
    departments.value = (data.dicts && data.dicts.department) || data.departments || []
    indicators.value = data.indicators || []
    fieldTemplates.value = data.field_templates || {}
    awardRanks.value = data.award_ranks || []
    roleRanks.value = data.role_ranks || []
    statuses.value = data.statuses || []
    attachmentCategories.value = data.attachment_categories || ['其他']
    if (!attachmentCategories.value.includes('其他')) attachmentCategories.value.push('其他')
  } catch (err) {
    // 统一错误处理
  }
}

function applyQuery() {
  const query = route.query || {}
  Object.keys(filters).forEach((key) => {
    if (query[key] !== undefined) filters[key] = String(query[key])
  })
  if (query.page) page.value = Number(query.page) || 1
  if (query.page_size) pageSize.value = Number(query.page_size) || 10
}

function syncQuery() {
  const query = {}
  Object.keys(filters).forEach((key) => {
    if (filters[key] !== '' && filters[key] !== null && filters[key] !== undefined) {
      query[key] = filters[key]
    }
  })
  if (page.value > 1) query.page = String(page.value)
  if (pageSize.value !== 10) query.page_size = String(pageSize.value)
  if (sort.value.prop) query.sort = sort.value.prop
  router.replace({ path: '/achievements', query }).catch(() => {})
}

function buildParams() {
  const params = { page: page.value, page_size: pageSize.value }
  Object.keys(filters).forEach((key) => {
    const value = filters[key]
    if (value !== '' && value !== null && value !== undefined) params[key] = value
  })
  if (sort.value.prop) params.sort = sort.value.prop
  return params
}

async function loadList() {
  loading.value = true
  try {
    const data = await achievementApi.list(buildParams())
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  syncQuery()
  loadList()
}

function handleReset() {
  Object.keys(filters).forEach((key) => {
    filters[key] = ''
  })
  sort.value = { prop: '-year', order: null }
  page.value = 1
  syncQuery()
  loadList()
}

function handleSizeChange() {
  page.value = 1
  loadList()
}

function handleSortChange({ prop, order }) {
  if (!prop || !order) {
    sort.value = { prop: '-year', order: null }
  } else {
    sort.value = { prop: order === 'ascending' ? prop : `-${prop}`, order }
  }
  page.value = 1
  syncQuery()
  loadList()
}

function filterByOwner(name) {
  filters.owner_name = name
  filters.keyword = ''
  page.value = 1
  syncQuery()
  loadList()
}

async function loadOwnerOptions(ownerType) {
  ownerOptions.value = []
  if (!isAdmin.value || !ownerType) return
  try {
    if (ownerType === 'teacher') {
      const list = await teacherApi.options()
      ownerOptions.value = list.map((item) => ({
        id: item.id,
        label: `${item.name}（${item.department || '未设院系'}）`
      }))
      advisorOptions.value = list
    } else {
      const list = await studentApi.options()
      ownerOptions.value = list.map((item) => ({
        id: item.id,
        label: `${item.name}（${item.student_no}）`
      }))
      try {
        advisorOptions.value = await teacherApi.options()
      } catch (err) {
        advisorOptions.value = []
      }
    }
  } catch (err) {
    ownerOptions.value = []
  }
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, emptyForm())
  dialogVisible.value = true
  loadOwnerOptions(form.owner_type)
}

function openEdit(row) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    id: row.id,
    owner_type: row.owner_type,
    owner_id: row.owner_id,
    category: row.category,
    title: row.title,
    year: row.year,
    academic_year: row.academic_year || academicYearOf(row.year),
    level: row.level || '',
    role_rank: row.role_rank || '',
    advisor_id: row.advisor_id || null,
    indicator_ids: (row.indicators || []).map((item) => item.id),
    extra: { ...(row.extra || {}) },
    description: row.description || '',
    status: row.status || ''
  })
  dialogVisible.value = true
  loadOwnerOptions(row.owner_type)
  drawerVisible.value = false
}

function handleOwnerTypeChange(value) {
  form.owner_id = null
  form.category = ''
  form.level = ''
  form.extra = {}
  loadOwnerOptions(value)
}

function handleYearChange(value) {
  form.academic_year = academicYearOf(value)
}

function resetForm() {
  if (formRef.value) formRef.value.clearValidate()
  Object.assign(form, emptyForm())
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      category: form.category,
      title: form.title.trim(),
      year: form.year,
      academic_year: form.academic_year,
      level: form.level,
      role_rank: form.role_rank,
      advisor_id: canPickAdvisor.value ? form.advisor_id : null,
      indicator_ids: form.indicator_ids,
      extra: form.extra,
      description: form.description
    }
    if (isAdmin.value) {
      payload.owner_type = form.owner_type
      payload.owner_id = form.owner_id
    }
    if (isElevated.value && form.status) payload.status = form.status
    if (dialogMode.value === 'create') {
      await achievementApi.create(payload)
      ElMessage.success('成果新增成功')
    } else {
      await achievementApi.update(form.id, payload)
      ElMessage.success('成果已更新')
    }
    dialogVisible.value = false
    await Promise.all([loadList(), loadMeta()])
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

function handleRowCommand(command, row) {
  if (command === 'submit') return handleSubmitReview(row)
  if (command === 'approve') return handleReview(row, 'approve', '材料齐全，审核通过')
  if (command === 'reject') return handleReject(row)
  if (command === 'indicators') return openIndicators(row)
  if (command === 'delete') return handleDelete(row)
}

function handleDelete(row) {
  ElMessageBox.confirm(
    `确认将成果「${row.title}」移入回收站吗？可在回收站恢复。`,
    '删除确认',
    { confirmButtonText: '移入回收站', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await achievementApi.remove(row.id)
      ElMessage.success('成果已移入回收站')
      if (items.value.length === 1 && page.value > 1) page.value -= 1
      loadList()
    })
    .catch(() => {})
}

async function handleSubmitReview(row) {
  try {
    await achievementApi.submit(row.id)
    ElMessage.success('已提交审核')
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

async function handleReview(row, action, comment) {
  try {
    await achievementApi.review(row.id, action, comment)
    ElMessage.success(action === 'approve' ? '已通过' : '已驳回')
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function handleReject(row) {
  ElMessageBox.prompt('请填写驳回意见，便于教师/学生修改后重新提交', '审核驳回', {
    confirmButtonText: '确认驳回',
    cancelButtonText: '取消',
    inputType: 'textarea',
    inputValidator: (value) => (value && value.trim() ? true : '驳回意见不能为空')
  })
    .then(({ value }) => handleReview(row, 'reject', value.trim()))
    .catch(() => {})
}

async function openIndicators(row) {
  const selected = (row.indicators || []).map((item) => item.id)
  try {
    const { value } = await ElMessageBox.prompt('输入要关联的指标点编号，用逗号分隔，例如 1,5,12', '关联认证指标点', {
      inputValue: selected.join(','),
      inputValidator: (text) => {
        const ids = text.split(/[,，\s]+/).filter(Boolean)
        if (!ids.length) return '请至少填写一个指标点编号'
        const valid = ids.every((id) => indicators.value.some((item) => String(item.id) === id))
        return valid ? true : '存在无效的指标点编号'
      }
    })
    const ids = value.split(/[,，\s]+/).filter(Boolean).map(Number)
    await achievementApi.update(row.id, { indicator_ids: ids })
    ElMessage.success('指标点已更新')
    loadList()
  } catch (err) {
    // 取消或统一错误处理
  }
}

function batchSetLevel() {
  const ids = selection.value.map((row) => row.id)
  ElMessageBox.prompt(
    `将 ${ids.length} 条成果的级别统一设置为（只对支持该级别的成果生效）`,
    '批量设置级别',
    {
      inputValidator: (value) => (value && value.trim() ? true : '请输入级别')
    }
  )
    .then(async ({ value }) => {
      const data = await achievementApi.batch('set_level', { ids, level: value.trim() })
      ElMessage.success(`已更新 ${data.affected} 条，跳过 ${data.skipped} 条`)
      selection.value = []
      loadList()
    })
    .catch(() => {})
}

function batchAddIndicators() {
  const ids = selection.value.map((row) => row.id)
  ElMessageBox.prompt('输入要追加关联的指标点编号，用逗号分隔，例如 1,5,12', '批量关联指标点', {
    inputValidator: (value) => {
      const list = (value || '').split(/[,，\s]+/).filter(Boolean)
      if (!list.length) return '请至少填写一个指标点编号'
      return list.every((id) => indicators.value.some((item) => String(item.id) === id))
        ? true
        : '存在无效的指标点编号'
    }
  })
    .then(async ({ value }) => {
      const list = value.split(/[,，\s]+/).filter(Boolean).map(Number)
      const data = await achievementApi.batch('add_indicators', { ids, indicator_ids: list })
      ElMessage.success(`已处理 ${data.affected} 条`)
      selection.value = []
      loadList()
    })
    .catch(() => {})
}

function batchSetStatus() {
  const ids = selection.value.map((row) => row.id)
  ElMessageBox.confirm('确认将所选成果全部标记为「已通过」吗？', '批量审核', {
    confirmButtonText: '全部通过',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      const data = await achievementApi.batch('set_status', { ids, status: 'approved' })
      ElMessage.success(`已处理 ${data.affected} 条`)
      selection.value = []
      loadList()
    })
    .catch(() => {})
}

function batchDelete() {
  const ids = selection.value.map((row) => row.id)
  ElMessageBox.confirm(`确认将所选 ${ids.length} 条成果移入回收站吗？`, '批量删除', {
    confirmButtonText: '移入回收站',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      const data = await achievementApi.batch('delete', { ids })
      ElMessage.success(`已处理 ${data.affected} 条`)
      selection.value = []
      loadList()
    })
    .catch(() => {})
}

function openDetail(row) {
  detail.value = row
  drawerVisible.value = true
}

function extraEntries(row) {
  if (!row || !row.extra_display) return []
  return Object.entries(row.extra_display).map(([label, value]) => ({ label, value }))
}

function openAttachments(row) {
  currentRow.value = row
  uploadCategory.value = '其他'
  attachmentVisible.value = true
  drawerVisible.value = false
  refreshRow(row.id)
}

async function refreshRow(id) {
  try {
    const data = await achievementApi.detail(id)
    currentRow.value = data
    const index = items.value.findIndex((item) => item.id === id)
    if (index >= 0) items.value[index] = data
    if (detail.value && detail.value.id === id) detail.value = data
  } catch (err) {
    // 统一错误处理
  }
}

async function handleUploadRequest(options) {
  if (!currentRow.value) return
  const file = options.file
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('单个文件不能超过 20MB')
    return
  }
  try {
    await achievementApi.uploadAttachments(currentRow.value.id, [file], uploadCategory.value)
    ElMessage.success('材料上传成功')
    await refreshRow(currentRow.value.id)
    loadList()
  } catch (err) {
    if (options.onError) options.onError(err)
  }
}

async function removeAttachment(row) {
  if (!currentRow.value) return
  ElMessageBox.confirm(`确认删除材料「${row.original_name}」吗？文件将被移除。`, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(async () => {
      await achievementApi.removeAttachment(currentRow.value.id, row.id)
      ElMessage.success('材料已删除')
      await refreshRow(currentRow.value.id)
      loadList()
    })
    .catch(() => {})
}

async function downloadAttachment(row, preview) {
  const achievementId = currentRow.value ? currentRow.value.id : detail.value && detail.value.id
  if (!achievementId) return
  try {
    const response = await achievementApi.downloadAttachment(achievementId, row.id, preview)
    if (preview) {
      openBlob(response)
    } else {
      saveBlob(response, row.original_name)
    }
  } catch (err) {
    // 统一错误处理
  }
}

async function handleExport() {
  try {
    const response = await ioApi.exportAchievements(buildParams())
    saveBlob(response, '业绩成果清单.xlsx')
  } catch (err) {
    // 统一错误处理
  }
}

onMounted(() => {
  applyQuery()
  loadMeta()
  loadList()
})
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  margin-bottom: 10px;
  background: #f0f7ff;
  border: 1px solid #d3e4ff;
  border-radius: 4px;
  font-size: 13px;
  color: #1f5fa9;
}

.muted {
  color: #909399;
  font-size: 12px;
}

.attachment-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.attachment-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.dialog-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: #606266;
}

.drawer-actions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
}
</style>