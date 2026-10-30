<template>
  <div class="flex min-h-screen items-center justify-center bg-zinc-50 p-4">
    <div class="w-full max-w-sm">
      <div class="mb-6 flex flex-col items-center text-center">
        <span
          class="mb-3 flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25"
        >
          <GraduationCap class="size-7" />
        </span>
        <h1 class="text-xl font-semibold tracking-tight">专业师生业绩管理系统</h1>
        <p class="mt-1.5 text-sm text-muted-foreground">
          面向工程教育认证的教师与学生业绩数据管理平台
        </p>
      </div>

      <div class="rounded-2xl border bg-white p-6 shadow-sm">
        <form class="space-y-4" @submit.prevent="handleSubmit">
          <div class="space-y-1.5">
            <Label for="username">登录名</Label>
            <div class="relative">
              <User class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="username"
                v-model="form.username"
                placeholder="请输入登录名"
                class="pl-9"
                autocomplete="username"
              />
            </div>
          </div>
          <div class="space-y-1.5">
            <Label for="password">密码</Label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="password"
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                class="pl-9"
                autocomplete="current-password"
              />
            </div>
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            <Loader2 v-if="loading" class="size-4 animate-spin" />
            {{ loading ? '登录中…' : '登 录' }}
          </Button>
        </form>

        <div class="mt-4 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2.5 text-xs leading-relaxed text-zinc-600">
          演示账号：管理员 admin / admin123；教师 teacher1 / 123456；学生 student1 / 123456
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { GraduationCap, Loader2, Lock, User } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function handleSubmit() {
  if (!form.username.trim()) {
    toast.error('请输入登录名')
    return
  }
  if (!form.password) {
    toast.error('请输入密码')
    return
  }
  loading.value = true
  try {
    const user = await userStore.login({ username: form.username.trim(), password: form.password })
    toast.success(`欢迎回来，${user.owner_name || user.username}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.replace(redirect)
  } catch (err) {
    // 错误提示已在请求拦截器中统一处理
  } finally {
    loading.value = false
  }
}
</script>