import request from './request'

function uploadForm(fields) {
  const form = new FormData()
  Object.entries(fields).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((item) => form.append(key, item))
    } else {
      form.append(key, value)
    }
  })
  return form
}

const multipart = { headers: { 'Content-Type': 'multipart/form-data' } }

export const authApi = {
  login: (data) => request.post('/auth/login', data),
  me: () => request.get('/auth/me'),
  refresh: (refreshToken) =>
    request.post('/auth/refresh', {}, {
      headers: { Authorization: `Bearer ${refreshToken}` }
    }),
  logout: () => request.post('/auth/logout'),
  changePassword: (data) => request.post('/auth/change-password', data)
}

export const metaApi = {
  options: () => request.get('/meta/options'),
  dictOptions: (kind) => request.get('/meta/dict-options', { params: { kind } }),
  advisorOptions: (params) => request.get('/meta/advisor-options', { params })
}

export const achievementApi = {
  list: (params) => request.get('/achievements/', { params }),
  trash: (params) => request.get('/achievements/trash', { params }),
  missingEvidence: (params) => request.get('/achievements/missing-evidence', { params }),
  detail: (id) => request.get(`/achievements/${id}`),
  create: (data) => request.post('/achievements/', data),
  update: (id, data) => request.put(`/achievements/${id}`, data),
  remove: (id, hard = false) =>
    request.delete(`/achievements/${id}`, { params: hard ? { hard: 1 } : {} }),
  restore: (id) => request.post(`/achievements/${id}/restore`),
  submit: (id) => request.post(`/achievements/${id}/submit`),
  review: (id, action, comment) =>
    request.post(`/achievements/${id}/review`, { action, comment }),
  batch: (action, payload) => request.post('/achievements/batch', { action, ...payload }),
  attachments: (id) => request.get(`/achievements/${id}/attachments`),
  uploadAttachments: (id, files, category) =>
    request.post(`/achievements/${id}/attachments`,
      uploadForm({ file: files, category }), multipart),
  removeAttachment: (id, attachmentId) =>
    request.delete(`/achievements/${id}/attachments/${attachmentId}`),
  attachmentUrl: (id, attachmentId) =>
    `/api/achievements/${id}/attachments/${attachmentId}/download`,
  downloadAttachment: (id, attachmentId, preview = false) =>
    request.get(`/achievements/${id}/attachments/${attachmentId}/download`, {
      params: preview ? { preview: 1 } : {},
      responseType: 'blob'
    }),
  // 旧接口（兼容保留）
  uploadAttachment: (id, file) =>
    request.post(`/achievements/${id}/attachment`, uploadForm({ file }), multipart),
  attachment: (id, preview) =>
    request.get(`/achievements/${id}/attachment`, {
      params: preview ? { preview: 1 } : {},
      responseType: 'blob'
    })
}

export const teacherApi = {
  list: (params) => request.get('/teachers/', { params }),
  options: () => request.get('/teachers/options'),
  detail: (id) => request.get(`/teachers/${id}`),
  profile: (id) => request.get(`/teachers/${id}/profile`),
  create: (data) => request.post('/teachers/', data),
  update: (id, data) => request.put(`/teachers/${id}`, data),
  remove: (id) => request.delete(`/teachers/${id}`)
}

export const studentApi = {
  list: (params) => request.get('/students/', { params }),
  options: () => request.get('/students/options'),
  detail: (id) => request.get(`/students/${id}`),
  profile: (id) => request.get(`/students/${id}/profile`),
  create: (data) => request.post('/students/', data),
  update: (id, data) => request.put(`/students/${id}`, data),
  remove: (id) => request.delete(`/students/${id}`)
}

export const userApi = {
  list: (params) => request.get('/users', { params }),
  candidates: (role) => request.get('/users/candidates', { params: { role } }),
  create: (data) => request.post('/users', data),
  update: (id, data) => request.put(`/users/${id}`, data),
  updateStatus: (id, isActive) => request.put(`/users/${id}/status`, { is_active: isActive }),
  resetPassword: (id, newPassword, mustChange = false) =>
    request.post(`/users/${id}/reset-password`,
      { new_password: newPassword, must_change_password: mustChange }),
  remove: (id) => request.delete(`/users/${id}`),
  unbind: (id) => request.post(`/users/${id}/unbind`)
}

export const statsApi = {
  overview: (params) => request.get('/stats/overview', { params }),
  dashboard: (params) => request.get('/stats/dashboard', { params }),
  breakdown: (dimension, params) =>
    request.get('/stats/breakdown', { params: { dimension, ...params } }),
  ranking: (params) => request.get('/stats/ranking', { params }),
  cross: (params) => request.get('/stats/cross', { params }),
  trend: (params) => request.get('/stats/trend', { params }),
  persons: (params) => request.get('/stats/persons', { params }),
  indicators: (params) => request.get('/stats/indicators', { params }),
  missingEvidence: (params) => request.get('/stats/missing-evidence', { params })
}

export const dictApi = {
  list: (params) => request.get('/dicts/', { params }),
  grouped: () => request.get('/dicts/grouped'),
  usage: () => request.get('/dicts/usage'),
  create: (data) => request.post('/dicts/', data),
  update: (id, data) => request.put(`/dicts/${id}`, data),
  remove: (id) => request.delete(`/dicts/${id}`),
  merge: (sourceId, targetId) =>
    request.post('/dicts/merge', { source_id: sourceId, target_id: targetId })
}

export const indicatorApi = {
  list: (params) => request.get('/indicators/', { params }),
  create: (data) => request.post('/indicators/', data),
  update: (id, data) => request.put(`/indicators/${id}`, data),
  remove: (id) => request.delete(`/indicators/${id}`),
  achievements: (id, params) => request.get(`/indicators/${id}/achievements`, { params })
}

export const advisorApi = {
  list: (params) => request.get('/advisors/', { params }),
  create: (data) => request.post('/advisors/', data),
  update: (id, data) => request.put(`/advisors/${id}`, data),
  remove: (id) => request.delete(`/advisors/${id}`),
  syncStudent: (studentId, teacherIds) =>
    request.post('/advisors/sync-student', { student_id: studentId, teacher_ids: teacherIds })
}

export const logApi = {
  list: (params) => request.get('/logs/', { params }),
  options: () => request.get('/logs/options'),
  summary: () => request.get('/logs/summary')
}

export const systemApi = {
  info: () => request.get('/system/info'),
  hints: () => request.get('/system/config-hints'),
  orphans: () => request.get('/system/orphans'),
  cleanupOrphans: () => request.post('/system/cleanup-orphans'),
  migrate: () => request.post('/system/migrate'),
  backups: () => request.get('/system/backups'),
  backup: () => request.post('/system/backup'),
  downloadBackup: (name) =>
    request.get('/system/backup/download', { params: { name }, responseType: 'blob' })
}

export const ioApi = {
  importTeachers: (file, options = {}) =>
    request.post('/import/teachers', uploadForm({ file, ...options }), multipart),
  importStudents: (file, options = {}) =>
    request.post('/import/students', uploadForm({ file, ...options }), multipart),
  importAchievements: (file, options = {}) =>
    request.post('/import/achievements', uploadForm({ file, ...options }), multipart),
  exportAchievements: (params) =>
    request.get('/export/achievements', { params, responseType: 'blob' }),
  exportReport: (params) =>
    request.get('/export/report', { params, responseType: 'blob' }),
  exportMissingEvidence: (params) =>
    request.get('/export/missing-evidence', { params, responseType: 'blob' }),
  exportPackage: (params) =>
    request.get('/export/package', { params, responseType: 'blob' }),
  teacherTemplate: () => request.get('/import/templates/teachers', { responseType: 'blob' }),
  studentTemplate: () => request.get('/import/templates/students', { responseType: 'blob' }),
  achievementTemplate: () =>
    request.get('/import/templates/achievements', { responseType: 'blob' })
}

export const healthApi = {
  health: () => request.get('/health')
}