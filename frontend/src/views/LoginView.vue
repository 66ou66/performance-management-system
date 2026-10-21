<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">专业师生业绩管理系统</h1>
      <p class="login-subtitle">面向工程教育认证的教师与学生业绩数据管理平台</p>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入登录名" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" :loading="loading" @click="handleSubmit">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-tips">
        演示账号：管理员 admin / admin123；教师 teacher1 / 123456；学生 student1 / 123456
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入登录名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const user = await userStore.login({ username: form.username.trim(), password: form.password })
    ElMessage.success(`欢迎回来，${user.owner_name || user.username}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.replace(redirect)
  } catch (err) {
    // 错误提示已在请求拦截器中统一处理
  } finally {
    loading.value = false
  }
}
</script>