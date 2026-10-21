<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">系统维护</h2>
        <p class="page-subtitle">运行状态、数据备份、孤儿附件清理与结构检查</p>
      </div>
      <el-button :icon="Refresh" @click="loadAll">刷新</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <div class="card">
          <h4 class="section-title">运行信息</h4>
          <el-descriptions v-if="info" :column="1" border size="small">
            <el-descriptions-item label="运行模式">
              <el-tag size="small" :type="info.app_env === 'production' ? 'success' : 'warning'">
                {{ info.app_env }}
              </el-tag>
              <el-tag v-if="info.debug" size="small" type="danger" style="margin-left: 6px">
                调试模式开启
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="成果数据">
              {{ info.coverage.achievements }} 条（回收站 {{ info.coverage.trash }} 条）
            </el-descriptions-item>
            <el-descriptions-item label="指标点 / 字典项">
              {{ info.coverage.indicators }} / {{ info.coverage.dict_items }}
            </el-descriptions-item>
            <el-descriptions-item label="操作日志">{{ info.coverage.logs }} 条</el-descriptions-item>
            <el-descriptions-item label="支撑材料文件">
              {{ info.upload_files }} 个（{{ info.upload_size }}）
            </el-descriptions-item>
            <el-descriptions-item label="送审模式">
              {{ info.require_review ? '开启（新成果需审核）' : '关闭（新成果直接通过）' }}
            </el-descriptions-item>
            <el-descriptions-item label="强制改密">
              {{ info.force_password_change ? '开启' : '关闭' }}
            </el-descriptions-item>
            <el-descriptions-item label="口令强度校验">
              {{ info.password_strength_check ? '开启' : '关闭' }}
            </el-descriptions-item>
            <el-descriptions-item label="上传上限">
              {{ info.max_upload_mb }} MB
            </el-descriptions-item>
            <el-descriptions-item label="CORS 白名单">
              <span class="mono">{{ (info.cors_origins || []).join(' , ') }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <h4 class="section-title">数据备份</h4>
          <p class="section-hint">
            备份包含数据库与 uploads 目录下的全部支撑材料，仅保留最近
            {{ backups.keep }} 份。
          </p>
          <el-button type="primary" :loading="backingUp" @click="createBackup">
            立即备份
          </el-button>
          <el-table
            :data="backups.items || []"
            v-loading="loading"
            border
            size="small"
            style="margin-top: 12px"
            empty-text="暂无备份"
          >
            <el-table-column prop="name" label="备份文件" min-width="180" show-overflow-tooltip />
            <el-table-column prop="size_text" label="大小" width="90" />
            <el-table-column prop="created_at" label="时间" width="160" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="card">
          <h4 class="section-title">数据一致性</h4>
          <p class="section-hint">
            孤儿附件指磁盘上已存在、但没有任何成果引用的文件（例如手工删除成果留下的残留）。
          </p>
          <el-alert
            :type="orphanTotal ? 'warning' : 'success'"
            :closable="false"
            show-icon
            :title="orphanTotal ? `发现 ${orphanTotal} 个孤儿文件` : '未发现孤儿文件'"
          />
          <div class="button-row">
            <el-button :loading="loading" @click="loadOrphans">重新扫描</el-button>
            <el-button type="warning" :disabled="!orphanTotal" @click="cleanup">
              清理孤儿文件
            </el-button>
            <el-button @click="runMigrate">检查数据结构</el-button>
          </div>
          <el-table
            v-if="orphanTotal"
            :data="(orphans.items || []).slice(0, 20)"
            border
            size="small"
            style="margin-top: 12px"
          >
            <el-table-column prop="path" label="文件" min-width="240" show-overflow-tooltip />
            <el-table-column prop="size_text" label="大小" width="90" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <div class="card">
      <h4 class="section-title">结构检查记录（迁移脚本执行明细）</h4>
      <el-table :data="migrationRows" border size="small" empty-text="本次启动未发生结构变更">
        <el-table-column prop="index" label="#" width="60" />
        <el-table-column prop="text" label="变更内容" min-width="400" />
      </el-table>
    </div>

    <div class="card">
      <h4 class="section-title">访问节流状态（登录失败锁定）</h4>
      <el-table :data="throttleRows" border size="small" empty-text="当前没有被锁定的账号">
        <el-table-column prop="key" label="账号" width="180" />
        <el-table-column prop="failures" label="近期失败次数" width="130" />
        <el-table-column prop="locked" label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.locked ? 'danger' : 'info'">
              {{ row.locked ? '已锁定' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { systemApi } from '../api'
import { formatSize, saveBlob } from '../utils/file'

const info = ref(null)
const backups = ref({ items: [], keep: 10 })
const orphans = ref({ items: [], total: 0 })
const loading = ref(false)
const backingUp = ref(false)

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
    ElMessage.success(`备份已生成：${data.name}（${formatSize(data.size)}）`)
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
  ElMessageBox.confirm(
    `确认删除 ${orphanTotal.value} 个未被引用的文件吗？该操作不会影响任何成果数据。`,
    '清理确认',
    { confirmButtonText: '清理', cancelButtonText: '取消', type: 'warning' }
  )
    .then(async () => {
      const data = await systemApi.cleanupOrphans()
      ElMessage.success(`已清理 ${data.removed} 个文件`)
      loadAll()
    })
    .catch(() => {})
}

async function runMigrate() {
  try {
    const data = await systemApi.migrate()
    const actions = data.actions || []
    if (actions.length) {
      ElMessage.success(`执行了 ${actions.length} 项结构变更`)
    } else {
      ElMessage.info('数据结构已是最新，无需变更')
    }
    loadAll()
  } catch (err) {
    // 统一错误处理
  }
}

onMounted(loadAll)
</script>

<style scoped>
.section-title {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}

.section-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #909399;
}

.button-row {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.mono {
  font-family: Consolas, Menlo, monospace;
  font-size: 12px;
}
</style>