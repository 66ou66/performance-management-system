<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">成果审核</h2>
        <p class="page-subtitle">
          教师与学生提交的业绩成果在此集中审核，审核通过后才计入统计与认证材料
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" @click="loadList">刷新</el-button>
        <el-button type="primary" :disabled="!selection.length" @click="batchApprove">
          批量通过（{{ selection.length }}）
        </el-button>
      </div>
    </div>

    <div class="card">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="status" style="width: 130px" @change="handleSearch">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="草稿" value="draft" />
            <el-option label="全部" value="" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="成果名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="items"
        v-loading="loading"
        border
        stripe
        empty-text="没有需要处理的成果"
        @selection-change="(rows) => (selection = rows)"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column prop="title" label="成果名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="所属人" width="140">
          <template #default="{ row }">
            {{ row.owner_name }}
            <el-tag size="small" effect="plain" type="info">{{ ownerTypeLabel(row.owner_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类型" width="115" />
        <el-table-column prop="level" label="级别" width="100" />
        <el-table-column prop="year" label="年份" width="80" />
        <el-table-column label="材料" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.attachment_count" size="small" type="success" effect="plain">
              {{ row.attachment_count }} 份
            </el-tag>
            <el-tag v-else size="small" type="danger" effect="plain">缺材料</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="提交时间" width="165" />
        <el-table-column prop="status" label="状态" width="95">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagTypes[row.status] || 'info'">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_comment" label="审核意见" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
            <el-button
              v-if="row.status !== 'approved'"
              link
              type="success"
              size="small"
              @click="approve(row)"
            >
              通过
            </el-button>
            <el-button
              v-if="row.status !== 'rejected'"
              link
              type="danger"
              size="small"
              @click="reject(row)"
            >
              驳回
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

    <el-drawer v-model="drawerVisible" title="成果审核详情" size="560px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="成果名称">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="所属人">
            {{ detail.owner_name }}（{{ ownerTypeLabel(detail.owner_type) }}）
          </el-descriptions-item>
          <el-descriptions-item label="院系">{{ detail.owner_department || '-' }}</el-descriptions-item>
          <el-descriptions-item label="类型 / 级别">
            {{ detail.category }} / {{ detail.level || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="年份 / 学年">
            {{ detail.year }} / {{ detail.academic_year || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="支撑材料">
            <div v-if="detail.attachments && detail.attachments.length">
              <div v-for="item in detail.attachments" :key="item.id" class="attachment-line">
                <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                <span>{{ item.original_name }}</span>
                <el-button link type="primary" size="small" @click="download(item)">下载</el-button>
              </div>
            </div>
            <span v-else class="muted">暂无支撑材料，建议驳回要求补充</span>
          </el-descriptions-item>
          <el-descriptions-item label="成果描述">
            <div style="white-space: pre-wrap">{{ detail.description || '暂无' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="审核意见">{{ detail.review_comment || '暂无' }}</el-descriptions-item>
        </el-descriptions>
        <el-input
          v-model="comment"
          type="textarea"
          :rows="3"
          placeholder="审核意见（驳回时必填）"
          class="comment-box"
        />
        <div class="drawer-actions">
          <el-button type="success" @click="approve(detail)">通过</el-button>
          <el-button type="danger" @click="reject(detail)">驳回</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { achievementApi } from '../api'
import { saveBlob, ownerTypeLabel, statusLabel, statusTagTypes } from '../utils/file'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const status = ref('pending')
const keyword = ref('')
const selection = ref([])
const drawerVisible = ref(false)
const detail = ref(null)
const comment = ref('')

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (status.value) params.status = status.value
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

function handleSearch() {
  page.value = 1
  loadList()
}

function handleSizeChange() {
  page.value = 1
  loadList()
}

function openDetail(row) {
  detail.value = row
  comment.value = ''
  drawerVisible.value = true
}

async function approve(row) {
  try {
    await achievementApi.review(row.id, 'approve', comment.value || '材料齐全，审核通过')
    ElMessage.success('已通过')
    drawerVisible.value = false
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function reject(row) {
  const prompt = row.id === (detail.value && detail.value.id) && comment.value
    ? Promise.resolve({ value: comment.value })
    : ElMessageBox.prompt('请填写驳回意见', '驳回成果', {
        confirmButtonText: '确认驳回',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputValidator: (value) => (value && value.trim() ? true : '驳回意见不能为空')
      })
  prompt
    .then(async ({ value }) => {
      await achievementApi.review(row.id, 'reject', value.trim())
      ElMessage.success('已驳回')
      drawerVisible.value = false
      loadList()
    })
    .catch(() => {})
}

async function batchApprove() {
  const ids = selection.value.map((row) => row.id)
  try {
    await ElMessageBox.confirm(`确认通过所选 ${ids.length} 条成果吗？`, '批量审核', {
      confirmButtonText: '全部通过',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (err) {
    return
  }
  try {
    const data = await achievementApi.batch('set_status', { ids, status: 'approved' })
    ElMessage.success(`已处理 ${data.affected} 条`)
    selection.value = []
    loadList()
  } catch (err) {
    // 统一错误处理
  }
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

<style scoped>
.attachment-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.muted {
  color: #909399;
  font-size: 12px;
}

.comment-box {
  margin-top: 14px;
}

.drawer-actions {
  margin-top: 14px;
  display: flex;
  gap: 10px;
}
</style>