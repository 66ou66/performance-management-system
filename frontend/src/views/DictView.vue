<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">基础字典管理</h2>
        <p class="page-subtitle">
          院系 / 专业 / 职称 / 年级的规范取值。统一字典可避免"计算机学院"与"计算机学院 "
          被统计成两个院系
        </p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增字典项</el-button>
    </div>

    <div class="card">
      <el-tabs v-model="activeKind" @tab-change="loadUsage">
        <el-tab-pane
          v-for="kind in kinds"
          :key="kind.value"
          :label="kind.label"
          :name="kind.value"
        />
      </el-tabs>

      <el-row :gutter="16">
        <el-col :span="14">
          <h4 class="section-title">已登记取值</h4>
          <el-table :data="currentItems" v-loading="loading" border stripe empty-text="暂无字典项">
            <el-table-column prop="name" label="名称" min-width="150" />
            <el-table-column label="别名" min-width="140">
              <template #default="{ row }">
                <span v-if="row.aliases && row.aliases.length">
                  {{ row.aliases.join('、') }}
                </span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="parent_name" label="上级" width="120">
              <template #default="{ row }">{{ row.parent_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="sort_order" label="排序" width="70" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button link type="primary" size="small" @click="openMerge(row)">合并</el-button>
                <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :span="10">
          <h4 class="section-title">数据中实际出现的取值</h4>
          <p class="section-hint">
            标记为「未登记」的取值建议补充进字典，或合并到已有取值上，以免统计口径分裂。
          </p>
          <el-table :data="usageRows" border stripe size="small" empty-text="暂无数据">
            <el-table-column prop="name" label="取值" min-width="130" />
            <el-table-column prop="count" label="记录数" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.registered ? 'success' : 'warning'">
                  {{ row.registered ? '已登记' : '未登记' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button
                  v-if="!row.registered"
                  link
                  type="primary"
                  size="small"
                  @click="quickRegister(row)"
                >
                  登记
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
      </el-row>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="form.id ? '编辑字典项' : '新增字典项'"
      width="520px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="类型">
          <el-input :model-value="kindLabel(form.kind)" disabled />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="120" />
        </el-form-item>
        <el-form-item label="别名">
          <el-input
            v-model="form.aliases"
            placeholder="多个别名用逗号分隔，导入/录入时会自动归一"
          />
        </el-form-item>
        <el-form-item v-if="form.kind === 'major'" label="所属院系">
          <el-select v-model="form.parent_name" clearable filterable allow-create style="width: 100%">
            <el-option v-for="item in departmentNames" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
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
const formRef = ref(null)
const form = reactive({
  id: null,
  kind: 'department',
  name: '',
  aliases: '',
  parent_name: '',
  sort_order: 0,
  is_active: true
})
const rules = {
  name: [{ required: true, message: '请输入字典项名称', trigger: 'blur' }]
}

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
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      kind: form.kind,
      name: form.name.trim(),
      aliases: form.aliases,
      parent_name: form.parent_name,
      sort_order: form.sort_order,
      is_active: form.is_active
    }
    if (form.id) {
      await dictApi.update(form.id, payload)
      ElMessage.success('字典项已更新')
    } else {
      await dictApi.create(payload)
      ElMessage.success('字典项已新增')
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
    ElMessage.warning('没有可合并的目标字典项')
    return
  }
  ElMessageBox.prompt(
    `将「${row.name}」合并到其它取值：现有数据会被改写，源字典项将被删除。`,
    '合并字典项',
    {
      inputPlaceholder: '请输入目标名称，例如：计算机学院',
      inputValidator: (value) => {
        const target = (value || '').trim()
        if (!target) return '请输入目标名称'
        if (target === row.name) return '目标不能与源相同'
        if (!options.some((item) => item.name === target)) return '目标必须是已登记的字典项'
        return true
      }
    }
  )
    .then(async ({ value }) => {
      const target = options.find((item) => item.name === value.trim())
      const data = await dictApi.merge(row.id, target.id)
      ElMessage.success(`已合并，更新了 ${data.affected} 条数据`)
      loadUsage()
    })
    .catch(() => {})
}

function remove(row) {
  ElMessageBox.confirm(
    `确认删除字典项「${row.name}」吗？存量数据中的取值不会被清除。`,
    '删除确认',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      await dictApi.remove(row.id)
      ElMessage.success('字典项已删除')
      loadUsage()
    })
    .catch(() => {})
}

onMounted(loadAll)
</script>

<style scoped>
.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: #303133;
}

.section-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #909399;
}

.muted {
  color: #909399;
}
</style>