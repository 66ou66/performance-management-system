<template>
  <div class="flex h-screen overflow-hidden bg-zinc-50">
    <!-- 侧栏 -->
    <aside class="flex w-60 shrink-0 flex-col bg-zinc-950 text-zinc-300">
      <div class="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
        <span class="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <GraduationCap class="size-5" />
        </span>
        <span class="text-[15px] font-semibold tracking-wide text-white">师生业绩管理</span>
      </div>

      <nav class="flex-1 space-y-1 overflow-y-auto px-2 py-3">
        <template v-for="item in visibleMenus" :key="item.path">
          <div v-if="item.children" class="py-1">
            <div class="px-3 pb-1.5 pt-2 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              {{ item.label }}
            </div>
            <button
              v-for="child in item.children"
              :key="child.path"
              type="button"
              class="flex w-full items-center rounded-md py-2 pl-8 pr-3 text-left text-sm transition-colors"
              :class="
                activeMenu === child.path
                  ? 'bg-white/10 font-medium text-white'
                  : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-100'
              "
              @click="router.push(child.path)"
            >
              {{ child.label }}
            </button>
          </div>
          <button
            v-else
            type="button"
            class="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors"
            :class="
              activeMenu === item.path
                ? 'bg-white/10 font-medium text-white'
                : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-100'
            "
            @click="router.push(item.path)"
          >
            <component :is="item.icon" class="size-4 shrink-0" />
            <span class="flex-1 text-left">{{ item.label }}</span>
            <Badge
              v-if="item.path === '/reviews' && pendingCount"
              class="h-5 min-w-5 px-1.5 text-[11px]"
              variant="destructive"
            >
              {{ pendingCount }}
            </Badge>
          </button>
        </template>
      </nav>

      <div class="flex items-center justify-between border-t border-white/10 px-4 py-3 text-xs text-zinc-500">
        <span>专业认证 · 数据支撑平台</span>
        <span v-if="envLabel" class="text-amber-400">{{ envLabel }}</span>
      </div>
    </aside>

    <!-- 主区 -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-14 shrink-0 items-center justify-between border-b bg-white px-5">
        <div class="flex items-center gap-3">
          <h1 class="text-base font-semibold">{{ currentTitle }}</h1>
          <span class="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">{{ today }}</span>
          <Badge v-if="userStore.hints && userStore.hints.require_review" variant="outline" class="text-amber-600">
            送审模式
          </Badge>
        </div>

        <div class="flex items-center gap-3">
          <Badge variant="secondary" :class="roleBadgeClass[userStore.role] || 'text-muted-foreground'">
            {{ roleLabel(userStore.role) }}
          </Badge>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" class="h-auto gap-2 px-2 py-1.5">
                <Avatar class="size-7">
                  <AvatarFallback class="bg-primary text-xs text-primary-foreground">{{ avatarText }}</AvatarFallback>
                </Avatar>
                <span class="text-sm font-medium">{{ userStore.displayName }}</span>
                <ChevronDown class="size-4 text-zinc-400" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-44">
              <DropdownMenuLabel class="text-xs text-zinc-500">{{ userStore.user?.username }}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem @click="router.push({ path: '/profile' })">
                <User class="size-4" /> 个人中心
              </DropdownMenuItem>
              <DropdownMenuItem @click="router.push({ path: '/profile', query: { tab: 'password' } })">
                <Lock class="size-4" /> 修改密码
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-destructive focus:text-destructive" @click="logoutOpen = true">
                <LogOut class="size-4" /> 退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto">
        <Alert v-if="userStore.mustChangePassword && route.path !== '/profile'" class="mx-4 mt-3">
          <TriangleAlert class="size-4" />
          <AlertTitle>当前账号需要修改初始密码</AlertTitle>
          <AlertDescription>为保障数据安全，请前往个人中心修改密码。</AlertDescription>
        </Alert>

        <router-view />
      </main>
    </div>

    <!-- 退出确认 -->
    <AlertDialog :open="logoutOpen" @update:open="logoutOpen = $event">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认退出登录？</AlertDialogTitle>
          <AlertDialogDescription>退出后需要重新输入账号密码才能访问系统。</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction @click="doLogout">退出</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  Award,
  BarChart3,
  ChevronDown,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Lock,
  LogOut,
  Settings,
  Trash2,
  TriangleAlert,
  Upload,
  User,
  Users
} from 'lucide-vue-next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { authApi, statsApi } from '../api'
import { useUserStore } from '../stores/user'
import { roleLabel } from '../utils/file'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const allMenus = [
  { path: '/dashboard', label: '数据看板', icon: LayoutDashboard },
  { path: '/achievements', label: '业绩成果管理', icon: Award },
  { path: '/reviews', label: '成果审核', icon: FileText, roles: ['admin', 'reviewer'] },
  { path: '/statistics', label: '统计报表', icon: BarChart3 },
  { path: '/trash', label: '回收站', icon: Trash2 },
  {
    path: 'archive',
    label: '档案管理',
    icon: Users,
    roles: ['admin', 'reviewer'],
    children: [
      { path: '/teachers', label: '教师信息管理' },
      { path: '/students', label: '学生信息管理' },
      { path: '/advisors', label: '指导关系管理' }
    ]
  },
  { path: '/advisors', label: '我的指导学生', icon: User, roles: ['teacher'] },
  {
    path: 'config',
    label: '配置与审计',
    icon: Settings,
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

const roleBadgeClass = {
  admin: 'text-destructive',
  reviewer: 'text-amber-600',
  teacher: 'text-primary',
  student: 'text-emerald-600'
}

const pendingCount = ref(0)
const logoutOpen = ref(false)

const visibleMenus = computed(() => allMenus.filter((item) => !item.roles || item.roles.includes(userStore.role)))
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
  () => loadPending(),
  { immediate: true }
)

async function doLogout() {
  logoutOpen.value = false
  try {
    await authApi.logout()
  } catch (err) {
    // 退出接口失败也要清理本地状态
  }
  userStore.logout()
  toast.success('已退出登录')
  router.replace('/login')
}
</script>