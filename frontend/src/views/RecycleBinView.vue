<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">回收站</h2>
        <p class="page-subtitle">
          删除的成果会先进入回收站，支撑材料一并保留，可随时恢复或彻底删除
        </p>
      </div>
      <div class="page-actions">
        <el-button type="primary" :disabled="!selection.length" @click="batchRestore">
          批量恢复（{{ selection.length }}）
        </el-button>
        <el-button
          v-if="isAdmin"
          type="danger"
          plain
          :disabled="!selection.length"
          @click="batchPurge"
        >
          批量彻底删除
        </el-button>
      </div>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="成果名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="category" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="items"
        v-loading="loading"
        border
        stripe
        empty-text="回收站为空"
        @selection-change="(rows) => (selection = rows)"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column prop="title" label="成果名称" min-width="240" show-overflow-tooltip />
        <el-table-column label="所属人" width="140">
          <template #default="{ row }">
            {{ row.owner_name }}
            <el-tag size="small" effect="plain" type="info">{{ ownerTypeLabel(row.owner_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类型" width="120" />
        <el-table-column prop="year" label="年份" width="80" />
        <el-table-column label="材料" width="90">
          <template #default="{ row }">{{ row.attachment_count || 0 }} 份</template>
        </el-table-column>
        <el-table-column label="删除时间" width="170">
          <template #default="{ row }">{{ row.deleted_at || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="restore(row)">恢复</el-button>
            <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
            <el-button v-if="isAdmin" link type="danger" size="small" @click="purge(row)">
              彻底删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadList"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="已删除成果详情" width="620px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="成果名称">{{ detail.title }}</el-descriptions-item>
        <el-descriptions-item label="所属人">
          {{ detail.owner_name }}（{{ ownerTypeLabel(detail.owner_type) }}）
        </el-descriptions-item>
        <el-descriptions-item label="类型 / 级别">
          {{ detail.category }} / {{ detail.level || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="年份">{{ detail.year }}</el-descriptions-item>
        <el-descriptions-item label="删除时间">{{ detail.deleted_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="支撑材料">
          <div v-if="detail.attachments && detail.attachments.length">
            <div v-for="item in detail.attachments" :key="item.id">
              {{ item.category }}：{{ item.original_name }}
            </div>
          </div>
          <span v-else class="muted">无</span>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="restore(detail)">恢复该成果</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshLeft, Search } from '@element-plus/icons-vue'
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
const category = ref('')
const categories = ref([])
const selection = ref([])
const detail = ref(null)
const detailVisible = ref(false)

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
    if (category.value) params.category = category.value
    const data = await achievementApi.trash(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  keyword.value = ''
  category.value = ''
  page.value = 1
  loadList()
}

function handleSizeChange() {
  page.value = 1
  loadList()
}

function openDetail(row) {
  detail.value = row
  detailVisible.value = true
}

async function restore(row) {
  if (!row) return
  try {
    await achievementApi.restore(row.id)
    ElMessage.success('成果已恢复')
    detailVisible.value = false
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function purge(row) {
  ElMessageBox.confirm(
    `彻底删除后「${row.title}」及其支撑材料将无法恢复，确认继续吗？`,
    '彻底删除',
    { confirmButtonText: '彻底删除', cancelButtonText: '取消', type: 'error' }
  )
    .then(async () => {
      await achievementApi.remove(row.id, true)
      ElMessage.success('已彻底删除')
      loadList()
    })
    .catch(() => {})
}

async function batchRestore() {
  const ids = selection.value.map((row) => row.id)
  try {
    const data = await achievementApi.batch('restore', { ids })
    ElMessage.success(`已恢复 ${data.affected} 条`)
    selection.value = []
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function batchPurge() {
  const ids = selection.value.map((row) => row.id)
  ElMessageBox.confirm(`确认彻底删除所选 ${ids.length} 条成果及其材料吗？`, '彻底删除', {
    confirmButtonText: '彻底删除',
    cancelButtonText: '取消',
    type: 'error'
  })
    .then(async () => {
      const data = await achievementApi.batch('purge', { ids })
      ElMessage.success(`已彻底删除 ${data.affected} 条`)
      selection.value = []
      loadList()
    })
    .catch(() => {})
}

onMounted(() => {
  loadMeta()
  loadList()
})
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
}

.muted {
  color: #909399;
  font-size: 12px;
}
</style>