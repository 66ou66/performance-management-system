import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('../layout/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('../views/DashboardView.vue'),
        meta: { title: '数据看板' }
      },
      {
        path: 'achievements',
        name: 'achievements',
        component: () => import('../views/AchievementListView.vue'),
        meta: { title: '业绩成果管理' }
      },
      {
        path: 'reviews',
        name: 'reviews',
        component: () => import('../views/ReviewView.vue'),
        meta: { title: '成果审核', roles: ['admin', 'reviewer'] }
      },
      {
        path: 'trash',
        name: 'trash',
        component: () => import('../views/RecycleBinView.vue'),
        meta: { title: '回收站' }
      },
      {
        path: 'statistics',
        name: 'statistics',
        component: () => import('../views/StatsView.vue'),
        meta: { title: '统计报表' }
      },
      {
        path: 'teachers',
        name: 'teachers',
        component: () => import('../views/TeacherListView.vue'),
        meta: { title: '教师信息管理', roles: ['admin', 'reviewer'] }
      },
      {
        path: 'students',
        name: 'students',
        component: () => import('../views/StudentListView.vue'),
        meta: { title: '学生信息管理', roles: ['admin', 'reviewer'] }
      },
      {
        path: 'advisors',
        name: 'advisors',
        component: () => import('../views/AdvisorView.vue'),
        meta: { title: '指导关系管理', roles: ['admin', 'reviewer', 'teacher'] }
      },
      {
        path: 'indicators',
        name: 'indicators',
        component: () => import('../views/IndicatorView.vue'),
        meta: { title: '认证指标点', roles: ['admin'] }
      },
      {
        path: 'dicts',
        name: 'dicts',
        component: () => import('../views/DictView.vue'),
        meta: { title: '基础字典管理', roles: ['admin'] }
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('../views/UserListView.vue'),
        meta: { title: '账号权限管理', roles: ['admin'] }
      },
      {
        path: 'logs',
        name: 'logs',
        component: () => import('../views/LogView.vue'),
        meta: { title: '操作日志审计', roles: ['admin'] }
      },
      {
        path: 'system',
        name: 'system',
        component: () => import('../views/SystemView.vue'),
        meta: { title: '系统维护', roles: ['admin'] }
      },
      {
        path: 'import-export',
        name: 'import-export',
        component: () => import('../views/ImportExportView.vue'),
        meta: { title: '数据导入导出', roles: ['admin'] }
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('../views/ProfileView.vue'),
        meta: { title: '个人中心' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach(async (to) => {
  document.title = to.meta.title ? `${to.meta.title} - 专业师生业绩管理系统` : '专业师生业绩管理系统'
  if (to.meta.public) {
    return true
  }
  const userStore = useUserStore()
  if (!userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!userStore.user) {
    const user = await userStore.fetchMe()
    if (!user) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    userStore.fetchHints()
  }
  const roles = to.meta.roles
  if (roles && roles.length && !roles.includes(userStore.role)) {
    return { path: '/dashboard' }
  }
  return true
})

export default router