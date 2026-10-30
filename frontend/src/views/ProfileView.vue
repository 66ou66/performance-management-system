<template>
  <div class="space-y-4 p-6">
    <div>
      <h2 class="text-xl font-semibold tracking-tight">个人中心</h2>
      <p class="mt-1 text-sm text-muted-foreground">查看账号信息、维护个人资料、管理本人业绩与修改登录密码</p>
    </div>

    <Alert v-if="userStore.mustChangePassword" class="border-amber-200 bg-amber-50">
      <TriangleAlert class="size-4 text-amber-600" />
      <AlertTitle class="text-amber-800">当前账号仍在使用初始密码</AlertTitle>
      <AlertDescription class="text-amber-700">
        请立即修改密码，避免他人使用初始密码登录查看或修改业绩数据。
      </AlertDescription>
    </Alert>

    <div class="grid gap-4 lg:grid-cols-2">
      <!-- 账号信息 -->
      <div class="rounded-xl border bg-white p-5 shadow-sm">
        <h4 class="mb-3 text-sm font-semibold">账号信息</h4>
        <dl class="space-y-3 text-sm">
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">登录名</dt><dd class="font-medium">{{ user?.username }}</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">角色</dt><dd>{{ roleLabel(user?.role) }}</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">关联人员</dt><dd>{{ user?.owner_name || '-' }}</dd></div>
          <div class="flex gap-2">
            <dt class="w-24 shrink-0 text-muted-foreground">账号状态</dt>
            <dd>
              <Badge :variant="user?.is_active ? 'secondary' : 'destructive'" :class="user?.is_active ? 'text-emerald-600' : ''">
                {{ user?.is_active ? '启用' : '禁用' }}
              </Badge>
            </dd>
          </div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">最近登录</dt><dd>{{ user?.last_login_at || '-' }}</dd></div>
          <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">创建时间</dt><dd>{{ user?.created_at }}</dd></div>
        </dl>
        <div v-if="advisors.length" class="mt-4 border-t pt-3">
          <div class="mb-2 text-sm font-medium">我的指导教师</div>
          <div class="flex flex-wrap gap-1.5">
            <Badge v-for="item in advisors" :key="item.id" variant="secondary">
              {{ item.teacher_name }}<span v-if="item.is_primary">（主导师）</span>
            </Badge>
          </div>
        </div>
      </div>

      <!-- 个人资料 -->
      <div class="rounded-xl border bg-white p-5 shadow-sm">
        <h4 class="mb-3 text-sm font-semibold">个人资料</h4>
        <div v-if="profileForm" class="space-y-3.5">
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="grid gap-1.5">
              <Label>{{ isTeacher ? '教师姓名' : '学生姓名' }}</Label>
              <Input v-model="profileForm.name" maxlength="80" />
            </div>
            <div v-if="isStudent" class="grid gap-1.5">
              <Label>学号</Label>
              <Input v-model="profileForm.student_no" disabled />
            </div>
            <div v-if="isTeacher" class="grid gap-1.5">
              <Label>职称</Label>
              <Input v-model="profileForm.title" disabled />
            </div>
            <div v-if="isStudent" class="grid gap-1.5">
              <Label>年级</Label>
              <Input v-model="profileForm.grade" disabled />
            </div>
            <div v-if="isStudent" class="grid gap-1.5">
              <Label>专业</Label>
              <Input v-model="profileForm.major" disabled />
            </div>
            <div v-if="isStudent" class="grid gap-1.5">
              <Label>班级</Label>
              <Input v-model="profileForm.class_name" disabled />
            </div>
            <div class="grid gap-1.5">
              <Label>所属院系</Label>
              <Input v-model="profileForm.department" disabled />
            </div>
            <div class="grid gap-1.5">
              <Label>邮箱</Label>
              <Input v-model="profileForm.email" maxlength="120" placeholder="用于接收审核结果通知" />
            </div>
            <div class="grid gap-1.5">
              <Label>联系电话</Label>
              <Input v-model="profileForm.phone" maxlength="30" />
            </div>
          </div>
          <div v-if="isTeacher" class="grid gap-1.5">
            <Label>研究方向</Label>
            <Textarea v-model="profileForm.research_area" rows="2" maxlength="200" />
          </div>
          <Alert v-if="isTeacher || isStudent">
            <Info class="size-4" />
            <AlertDescription>
              学号、年级、专业、班级、职称与院系属于认证统计数据，如需变更请联系管理员，以免影响统计口径。
            </AlertDescription>
          </Alert>
          <Button v-if="isTeacher || isStudent" :disabled="savingProfile" @click="handleSaveProfile">
            保存资料
          </Button>
          <Alert v-else>
            <Info class="size-4" />
            <AlertDescription>管理员/审核员账号不绑定人员档案，如需修改登录名请前往账号权限管理。</AlertDescription>
          </Alert>
        </div>
        <div v-else class="py-8 text-center text-sm text-muted-foreground">暂无个人档案</div>
      </div>
    </div>

    <!-- 我的成果 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <div class="flex items-center justify-between border-b px-4 py-3">
        <span class="text-sm font-medium">我的业绩成果（{{ myAchievements.length }} 条）</span>
        <Button variant="link" class="h-auto p-0" @click="router.push('/achievements')">前往管理</Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>成果名称</TableHead>
            <TableHead class="w-[130px]">院系</TableHead>
            <TableHead class="w-[120px]">成果类型</TableHead>
            <TableHead class="w-[100px]">级别</TableHead>
            <TableHead class="w-[80px]">年份</TableHead>
            <TableHead class="w-[100px]">状态</TableHead>
            <TableHead class="w-[90px]">材料</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in myAchievements" :key="row.id">
            <TableCell class="max-w-[240px] truncate font-medium">{{ row.title }}</TableCell>
            <TableCell class="max-w-[130px] truncate text-muted-foreground">{{ row.owner_department || '-' }}</TableCell>
            <TableCell>{{ row.category }}</TableCell>
            <TableCell>{{ row.level || '-' }}</TableCell>
            <TableCell>{{ row.year }}</TableCell>
            <TableCell>
              <Badge variant="secondary" :class="statusBadgeClass[row.status] || 'text-muted-foreground'">{{ statusLabel(row.status) }}</Badge>
            </TableCell>
            <TableCell>
              <Badge v-if="row.attachment_count" variant="secondary" class="text-emerald-600">{{ row.attachment_count }} 份</Badge>
              <Badge v-else variant="secondary" class="text-destructive">缺材料</Badge>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!myAchievements.length" :colspan="7">暂无业绩数据</TableEmpty>
        </TableBody>
      </Table>
    </div>

    <!-- 修改密码 -->
    <div ref="passwordCardRef" class="max-w-[620px] rounded-xl border bg-white p-5 shadow-sm">
      <h4 class="mb-3 text-sm font-semibold">修改密码</h4>
      <div class="space-y-3.5">
        <div class="grid gap-1.5">
          <Label>原密码</Label>
          <Input v-model="passwordForm.old_password" type="password" placeholder="请输入原密码" />
        </div>
        <div class="grid gap-1.5">
          <Label>新密码</Label>
          <Input v-model="passwordForm.new_password" type="password" :placeholder="`长度不少于 ${minPasswordLength} 位`" />
        </div>
        <div class="grid gap-1.5">
          <Label>确认密码</Label>
          <Input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码" />
        </div>
        <Alert>
          <Info class="size-4" />
          <AlertDescription>修改成功后其他设备上的登录会立即失效，需要重新登录。</AlertDescription>
        </Alert>
        <Button :disabled="savingPassword" @click="handleChangePassword">修改密码</Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Info, TriangleAlert } from 'lucide-vue-next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { achievementApi, authApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'
import { roleLabel, statusLabel } from '../utils/file'

const statusBadgeClass = {
  draft: 'text-zinc-500',
  pending: 'text-amber-600',
  approved: 'text-emerald-600',
  rejected: 'text-destructive'
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const user = computed(() => userStore.user)
const isTeacher = computed(() => userStore.role === 'teacher')
const isStudent = computed(() => userStore.role === 'student')
const advisors = computed(() => (userStore.user && userStore.user.advisors) || [])
const minPasswordLength = computed(() => (userStore.hints && userStore.hints.min_password_length) || 6)

const profileForm = ref(null)
const savingProfile = ref(false)
const myAchievements = ref([])
const passwordCardRef = ref(null)
const savingPassword = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

function initProfile() {
  const profile = userStore.user && userStore.user.profile
  if (!profile) {
    profileForm.value = null
    return
  }
  profileForm.value = {
    id: profile.id,
    name: profile.name || '',
    student_no: profile.student_no || '',
    class_name: profile.class_name || '',
    title: profile.title || '',
    grade: profile.grade || '',
    major: profile.major || '',
    department: profile.department || '',
    email: profile.email || '',
    phone: profile.phone || '',
    research_area: profile.research_area || ''
  }
}

async function loadMyAchievements() {
  try {
    const data = await achievementApi.list({ page: 1, page_size: 100 })
    myAchievements.value = data.items || []
  } catch (err) {
    myAchievements.value = []
  }
}

async function handleSaveProfile() {
  if (!profileForm.value) return
  savingProfile.value = true
  try {
    if (isTeacher.value) {
      await teacherApi.update(profileForm.value.id, {
        name: profileForm.value.name.trim(),
        email: profileForm.value.email,
        phone: profileForm.value.phone,
        research_area: profileForm.value.research_area
      })
    } else {
      await studentApi.update(profileForm.value.id, {
        name: profileForm.value.name.trim(),
        email: profileForm.value.email,
        phone: profileForm.value.phone
      })
    }
    toast.success('个人资料已更新')
    await userStore.fetchMe()
    initProfile()
  } catch (err) {
    // 统一错误处理
  } finally {
    savingProfile.value = false
  }
}

function validatePassword() {
  if (!passwordForm.old_password) {
    toast.error('请输入原密码')
    return false
  }
  if (!passwordForm.new_password || passwordForm.new_password.length < minPasswordLength.value) {
    toast.error(`新密码长度不能少于 ${minPasswordLength.value} 位`)
    return false
  }
  if (!passwordForm.confirm_password || passwordForm.confirm_password !== passwordForm.new_password) {
    toast.error('两次输入的密码不一致')
    return false
  }
  return true
}

async function handleChangePassword() {
  if (!validatePassword()) return
  savingPassword.value = true
  try {
    const data = await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    userStore.applyAuth(data)
    toast.success('密码修改成功，其他设备上的登录已失效')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (err) {
    // 统一错误处理
  } finally {
    savingPassword.value = false
  }
}

onMounted(async () => {
  if (!userStore.user) {
    await userStore.fetchMe()
  }
  if (!userStore.hints) {
    userStore.fetchHints()
  }
  initProfile()
  loadMyAchievements()
  if (route.query.tab === 'password' && passwordCardRef.value) {
    passwordCardRef.value.scrollIntoView({ behavior: 'smooth' })
  }
})
</script>