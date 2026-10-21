import { defineStore } from 'pinia'
import { authApi, systemApi } from '../api'
import {
  clearToken,
  getRefreshToken,
  getToken,
  setRefreshToken,
  setToken
} from '../api/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    user: null,
    hints: null
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    role: (state) => (state.user ? state.user.role : ''),
    isAdmin: (state) => Boolean(state.user) && state.user.role === 'admin',
    isReviewer: (state) => Boolean(state.user) && state.user.role === 'reviewer',
    isElevated: (state) =>
      Boolean(state.user) && ['admin', 'reviewer'].includes(state.user.role),
    canManage: (state) => Boolean(state.user) && state.user.role === 'admin',
    displayName: (state) => {
      if (!state.user) return ''
      return state.user.owner_name || state.user.username
    },
    profile: (state) => (state.user ? state.user.profile : null),
    mustChangePassword: (state) =>
      Boolean(state.user) && state.user.must_change_password === true
  },
  actions: {
    async login(payload) {
      const data = await authApi.login(payload)
      this.applyAuth(data)
      return data.user
    },
    applyAuth(data) {
      this.token = data.access_token
      this.user = data.user
      setToken(data.access_token)
      if (data.refresh_token) {
        setRefreshToken(data.refresh_token)
      }
    },
    async fetchMe() {
      if (!this.token) return null
      try {
        const data = await authApi.me()
        this.user = data
        return data
      } catch (err) {
        this.logout()
        return null
      }
    },
    async fetchHints() {
      if (!this.token) return null
      try {
        this.hints = await systemApi.hints()
      } catch (err) {
        this.hints = null
      }
      return this.hints
    },
    hasRefreshToken() {
      return Boolean(getRefreshToken())
    },
    logout() {
      this.token = ''
      this.user = null
      clearToken()
    }
  }
})