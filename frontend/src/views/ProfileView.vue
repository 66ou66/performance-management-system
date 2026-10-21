<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">个人中心</h2>
        <p class="page-subtitle">查看账号信息、维护个人资料、管理本人业绩与修改登录密码</p>
      </div>
    </div>

    <el-alert
      v-if="userStore.mustChangePassword"
      type="warning"
      :closable="false"
      show-icon
      class="mb"
      title="当前账号仍在使用初始密码"
      description="请立即修改密码，避免他人使用初始密码登录查看或修改业绩数据。"
    />

    <div class="chart-grid" style="margin-top: 0">
      <div class="card">
        <div class="chart-title">账号信息</div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="登录名">{{ user?.username }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ roleLabel(user?.role) }}</el-descriptions-item>
          <el-descriptions-item label="关联人员">{{ user?.owner_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="账号状态">
            <el-tag :type="user?.is_active ? 'success' : 'danger'" size="small">
              {{ user?.is_active ? '启用' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最近登录">{{ user?.last_login_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ user?.created_at }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="advisors.length" class="advisor-box">
          <div class="chart-title" style="font-size: 13px">我的指导教师</div>
          <el-tag v-for="item in advisors" :key="item.id" style="margin-right: 6px">
            {{ item.teacher_name }}
            <span v-if="item.is_primary">（主导师）</span>
          </el-tag>
        </div>
      </div>

      <div class="card">
        <div class="chart-title">个人资料</div>
        <el-form v-if="profileForm" ref="profileFormRef" :model="profileForm" label-width="110px">
          <el-form-item :label="isTeacher ? '教师姓名' : '学生姓名'">
            <el-input v-model="profileForm.name" maxlength="80" />
          </el-form-item>
          <el-form-item v-if="isStudent" label="学号">
            <el-input v-model="profileForm.student_no" disabled />
          </el-form-item>
          <el-form-item v-if="isTeacher" label="职称">
            <el-input v-model="profileForm.title" disabled />
          </el-form-item>
          <el-form-item v-if="isStudent" label="年级">
            <el-input v-model="profileForm.grade" disabled />
          </el-form-item>
          <el-form-item v-if="isStudent" label="专业">
            <el-input v-model="profileForm.major" disabled />
          </el-form-item>
          <el-form-item v-if="isStudent" label="班级">
            <el-input v-model="profileForm.class_name" disabled />
          </el-form-item>
          <el-form-item label="所属院系">
            <el-input v-model="profileForm.department" disabled />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="profileForm.email" maxlength="120" placeholder="用于接收审核结果通知" />
          </el-form-item>
          <el-form-item label="联系电话">
            <el-input v-model="profileForm.phone" maxlength="30" />
          </el-form-item>
          <el-form-item v-if="isTeacher" label="研究方向">
            <el-input v-model="profileForm.research_area" maxlength="200" type="textarea" :rows="2" />
          </el-form-item>
          <el-alert
            v-if="isTeacher || isStudent"
            type="info"
            :closable="false"
            show-icon
            title="学号、年级、专业、班级、职称与院系属于认证统计数据，如需变更请联系管理员，以免影响统计口径。"
          />
          <el-form-item v-if="isTeacher || isStudent" style="margin-top: 12px">
            <el-button type="primary" :loading="savingProfile" @click="handleSaveProfile">
              保存资料
            </el-button>
          </el-form-item>
          <el-alert
            v-else
            type="info"
            :closable="false"
            show-icon
            title="管理员/审核员账号不绑定人员档案，如需修改登录名请前往账号权限管理。"
          />
        </el-form>
        <el-empty v-else description="暂无个人档案" :image-size="70" />
      </div>
    </div>

    <div class="card">
      <div class="table-toolbar">
        <span class="chart-title" style="margin: 0">我的业绩成果（{{ myAchievements.length }} 条）</span>
        <el-button text type="primary" @click="router.push('/achievements')">前往管理</el-button>
      </div>
      <el-table :data="myAchievements" border size="small" empty-text="暂无业绩数据">
        <el-table-column prop="title" label="成果名称" min-width="240" show-overflow-tooltip />
        <el-table-column prop="owner_department" label="院系" width="130" show-overflow-tooltip />
        <el-table-column prop="category" label="成果类型" width="120" />
        <el-table-column prop="level" label="级别" width="100" />
        <el-table-column prop="year" label="年份" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagTypes[row.status] || 'info'">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="材料" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.attachment_count" size="small" type="success" effect="plain">
              {{ row.attachment_count }} 份
            </el-tag>
            <el-tag v-else size="small" type="danger" effect="plain">缺材料</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card" style="max-width: 620px">
      <div class="chart-title">修改密码</div>
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="110px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
            :placeholder="`长度不少于 ${minPasswordLength} 位`"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="修改成功后其他设备上的登录会立即失效，需要重新登录。"
          style="margin-bottom: 12px"
        />
        <el-form-item>
          <el-button type="primary" :loading="savingPassword" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { achievementApi, authApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'
import { roleLabel, statusLabel, statusTagTypes } from '../utils/file'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const user = computed(() => userStore.user)
const isTeacher = computed(() => userStore.role === 'teacher')
const isStudent = computed(() => userStore.role === 'student')
const advisors = computed(() => (userStore.user && userStore.user.advisors) || [])
const minPasswordLength = computed(
  () => (userStore.hints && userStore.hints.min_password_length) || 6
)

const profileFormRef = ref(null)
const profileForm = ref(null)
const savingProfile = ref(false)
const myAchievements = ref([])

const passwordFormRef = ref(null)
const savingPassword = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

function validateConfirm(rule, value, callback) {
  if (!value) {
    callback(new Error('请再次输入新密码'))
    return
  }
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码长度不能少于 6 位', trigger: 'blur' }
  ],
  confirm_password: [{ validator: validateConfirm, trigger: 'blur' }]
}

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
    ElMessage.success('个人资料已更新')
    await userStore.fetchMe()
    initProfile()
  } catch (err) {
    // 统一错误处理
  } finally {
    savingProfile.value = false
  }
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  savingPassword.value = true
  try {
    const data = await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    // 后端会递增令牌版本，旧令牌立即失效，这里必须换成新令牌
    userStore.applyAuth(data)
    ElMessage.success('密码修改成功，其他设备上的登录已失效')
    passwordFormRef.value.resetFields()
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
  if (route.query.tab === 'password' && passwordFormRef.value) {
    passwordFormRef.value.$el && passwordFormRef.value.$el.scrollIntoView({ behavior: 'smooth' })
  }
})
</script>

<style scoped>
.mb {
  margin-bottom: 12px;
}

.advisor-box {
  margin-top: 12px;
}
</style>