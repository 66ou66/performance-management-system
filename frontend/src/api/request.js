import axios from 'axios'
import { ElMessage } from 'element-plus'

const TOKEN_KEY = 'achievement_token'
const REFRESH_KEY = 'achievement_refresh_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function setRefreshToken(token) {
  if (token) {
    localStorage.setItem(REFRESH_KEY, token)
  } else {
    localStorage.removeItem(REFRESH_KEY)
  }
}

export function setTokens(accessToken, refreshToken) {
  setToken(accessToken)
  setRefreshToken(refreshToken)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function redirectToLogin() {
  clearToken()
  if (!window.location.hash.startsWith('#/login')) {
    window.location.hash = '#/login'
  }
}

// 访问令牌过期时用刷新令牌静默续期，避免用户正在填表时被踢回登录页
let refreshing = null

async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return ''
  if (!refreshing) {
    refreshing = axios
      .post('/api/auth/refresh', {}, {
        headers: { Authorization: `Bearer ${refreshToken}` }
      })
      .then((response) => {
        const payload = response.data
        if (payload && payload.code === 0 && payload.data && payload.data.access_token) {
          setToken(payload.data.access_token)
          return payload.data.access_token
        }
        return ''
      })
      .catch(() => '')
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

function parseBlobError(data) {
  return data.text().then((text) => {
    try {
      const payload = JSON.parse(text)
      return (payload && payload.message) || ''
    } catch (err) {
      return ''
    }
  })
}

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response
    }
    const payload = response.data
    if (payload && payload.code === 0) {
      return payload.data
    }
    const message = (payload && payload.message) || '请求失败'
    ElMessage.error(message)
    return Promise.reject(new Error(message))
  },
  async (error) => {
    const config = error.config || {}
    const status = error.response && error.response.status
    let message = '网络异常，请稍后重试'
    const data = error.response && error.response.data
    if (data instanceof Blob) {
      const parsed = await parseBlobError(data)
      if (parsed) message = parsed
    } else if (data && data.message) {
      message = data.message
    } else if (error.message) {
      message = error.message
    }

    // 令牌过期：续期一次后重放原请求
    // 注意只有登录/刷新这两个接口本身不触发续期与跳转，/auth/me 等仍按普通受保护接口处理
    const isAuthUrl = ['/auth/login', '/auth/refresh'].some((path) =>
      (config.url || '').includes(path)
    )
    if (status === 401 && !config.__retried && !isAuthUrl && getRefreshToken()) {
      config.__retried = true
      const token = await refreshAccessToken()
      if (token) {
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${token}`
        return request(config)
      }
    }

    if (status === 401) {
      if (isAuthUrl) {
        // 登录/刷新失败：直接把服务端提示显示出来，不再重复跳转
        ElMessage.error(message)
      } else {
        ElMessage.error('登录已过期，请重新登录')
        redirectToLogin()
      }
      return Promise.reject(new Error(message))
    }

    ElMessage.error(message)
    return Promise.reject(new Error(message))
  }
)

export default request