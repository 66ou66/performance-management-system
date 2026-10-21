<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="brand">
        <el-icon :size="22"><DataAnalysis /></el-icon>
        <span>师生业绩管理</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
        background-color="#1f2d3d"
        text-color="#c6ccd8"
        active-text-color="#ffffff"
        :collapse="false"
      >
        <template v-for="item in visibleMenus" :key="item.path">
          <el-menu-item v-if="!item.children" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
            <el-badge
              v-if="item.path === '/reviews' && pendingCount"
              :value="pendingCount"
              class="menu-badge"
            />
          </el-menu-item>
          <el-sub-menu v-else :index="item.path">
            <template #title>
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </template>
            <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path">
              {{ child.label }}
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
      <div class="sidebar-footer">
        <span>专业认证 · 数据支撑平台</span>
        <span v-if="envLabel" class="env-tag">{{ envLabel }}</span>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span class="header-title">{{ currentTitle }}</span>
          <el-tag size="small" effect="plain" type="info">{{ today }}</el-tag>
          <el-tag v-if="userStore.hints && userStore.hints.require_review" size="small" type="warning" effect="light">
            送审模式
          </el-tag>
        </div>
        <div class="header-right">
          <el-tag :type="roleTagTypes[userStore.role] || 'info'" effect="light" size="small">
            {{ roleLabel(userStore.role) }}
          </el-tag>
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-entry">
              <el-avatar :size="30" class="avatar">{{ avatarText }}</el-avatar>
              <span class="username">{{ userStore.displayName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人中心
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon> 修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <el-alert
          v-if="userStore.mustChangePassword && route.path !== '/profile'"
          type="warning"
          :closable="false"
          show-icon
          class="global-alert"
          title="当前账号需要修改初始密码"
          description="为保障数据安全，请前往个人中心修改密码。"
        />
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Avatar,
  DataAnalysis,
  DataLine,
  Delete,
  Document,
  Lock,
  Medal,
  Setting,
  SwitchButton,
  TrendCharts,
  Upload,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { statsApi, authApi } from '../api'
import { useUserStore } from '../stores/user'
import { roleLabel, roleTagTypes } from '../utils/file'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const allMenus = [
  { path: '/dashboard', label: '数据看板', icon: DataLine },
  { path: '/achievements', label: '业绩成果管理', icon: Medal },
  { path: '/reviews', label: '成果审核', icon: Document, roles: ['admin', 'reviewer'] },
  { path: '/statistics', label: '统计报表', icon: TrendCharts },
  { path: '/trash', label: '回收站', icon: Delete },
  {
    path: 'archive',
    label: '档案管理',
    icon: UserFilled,
    roles: ['admin', 'reviewer'],
    children: [
      { path: '/teachers', label: '教师信息管理' },
      { path: '/students', label: '学生信息管理' },
      { path: '/advisors', label: '指导关系管理' }
    ]
  },
  { path: '/advisors', label: '我的指导学生', icon: Avatar, roles: ['teacher'] },
  {
    path: 'config',
    label: '配置与审计',
    icon: Setting,
    roles: ['admin'],
    children: [
      { path: '/users', label: '账号权限管理' },
      { path: '/indicators', label: '认证指标点' },
      { path: '/dicts', label: '基础字典管理' },
      { path: '/logs', label: '操作日志审计' },
      { path: '/system', label: '系统维护' }
    ]
  },
  { path: '/import-export', label: '数据导入导出', icon: Upload, roles: ['admin'] },
  { path: '/profile', label: '个人中心', icon: User }
]

const pendingCount = ref(0)

const visibleMenus = computed(() =>
  allMenus.filter((item) => !item.roles || item.roles.includes(userStore.role))
)

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '专业师生业绩管理系统')
const avatarText = computed(() => (userStore.displayName || 'U').slice(0, 1))
const envLabel = computed(() => {
  const env = userStore.hints && userStore.hints.app_env
  if (!env || env === 'development') return ''
  return env === 'production' ? '生产环境' : env
})
const today = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  weekday: 'long'
})

async function loadPending() {
  if (!userStore.isElevated) {
    pendingCount.value = 0
    return
  }
  try {
    const data = await statsApi.overview({ status: 'pending' })
    pendingCount.value = (data.counts && data.counts.pending) || 0
  } catch (err) {
    pendingCount.value = 0
  }
}

watch(
  () => [userStore.role, route.path],
  () => {
    loadPending()
  },
  { immediate: true }
)

function handleCommand(command) {
  if (command === 'profile' || command === 'password') {
    router.push({ path: '/profile', query: command === 'password' ? { tab: 'password' } : {} })
    return
  }
  if (command === 'logout') {
    ElMessageBox.confirm('确认退出当前登录账号吗？', '提示', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning'
    })
      .then(() => {
        try {
          authApi.logout()
        } catch (err) {
          // 退出接口失败也要清理本地状态
        }
        userStore.logout()
        ElMessage.success('已退出登录')
        router.replace('/login')
      })
      .catch(() => {})
  }
}
</script>

<style scoped>
.layout {
  height: 100vh;
}

.sidebar {
  background: var(--app-sidebar);
  display: flex;
  flex-direction: column;
  color: #fff;
  overflow: hidden;
}

.brand {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}

.menu :deep(.el-menu-item.is-active) {
  background-color: var(--app-primary) !important;
}

.menu-badge {
  margin-left: 8px;
}

.menu-badge :deep(.el-badge__content) {
  border: none;
}

.sidebar-footer {
  padding: 12px 18px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.env-tag {
  color: #ffd04b;
}

.header {
  height: 60px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 8px rgba(31, 45, 61, 0.06);
  padding: 0 22px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.avatar {
  background: var(--app-primary);
  color: #fff;
  font-size: 14px;
}

.username {
  font-size: 14px;
  color: #303133;
}

.main {
  background: var(--app-bg);
  padding: 0;
  overflow-y: auto;
}

.global-alert {
  margin: 12px 16px 0;
}
</style>