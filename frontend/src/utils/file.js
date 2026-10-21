import { ElMessage } from 'element-plus'

export function saveBlob(response, fallbackName) {
  const blob = response.data
  const contentType = (response.headers && response.headers['content-type']) || ''
  if (contentType.includes('application/json')) {
    const reader = new FileReader()
    reader.onload = () => {
      let message = '文件下载失败'
      try {
        const payload = JSON.parse(reader.result)
        message = payload.message || message
      } catch (err) {
        message = '文件下载失败'
      }
      ElMessage.error(message)
    }
    reader.readAsText(blob)
    return
  }
  let filename = fallbackName
  const disposition = (response.headers && response.headers['content-disposition']) || ''
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
  if (utf8Match) {
    filename = decodeURIComponent(utf8Match[1])
  } else if (plainMatch) {
    filename = decodeURIComponent(plainMatch[1])
  } else {
    const stamp = new Date()
      .toISOString()
      .slice(0, 19)
      .replace(/[-:T]/g, '')
    const dot = (fallbackName || 'download').lastIndexOf('.')
    filename = dot > 0
      ? `${fallbackName.slice(0, dot)}_${stamp}${fallbackName.slice(dot)}`
      : `${fallbackName}_${stamp}`
  }
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
  ElMessage.success('文件已开始下载')
}

export function openBlob(response) {
  const blob = response.data
  const url = window.URL.createObjectURL(blob)
  const opened = window.open(url, '_blank')
  if (!opened) {
    ElMessage.warning('浏览器阻止了新窗口，请允许弹窗后重试')
  }
  setTimeout(() => window.URL.revokeObjectURL(url), 60000)
}

export function formatSize(size) {
  const value = Number(size) || 0
  if (value <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let amount = value
  let index = 0
  while (amount >= 1024 && index < units.length - 1) {
    amount /= 1024
    index += 1
  }
  const digits = index === 0 ? 0 : 1
  return `${amount.toFixed(digits)} ${units[index]}`
}

export const roleLabels = {
  admin: '管理员',
  reviewer: '审核员',
  teacher: '教师',
  student: '学生'
}

export const roleTagTypes = {
  admin: 'danger',
  reviewer: 'warning',
  teacher: 'primary',
  student: 'success'
}

export const statusLabels = {
  draft: '草稿',
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回'
}

export const statusTagTypes = {
  draft: 'info',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger'
}

export function roleLabel(role) {
  return roleLabels[role] || role || '-'
}

export function statusLabel(status) {
  return statusLabels[status] || status || '-'
}

export function ownerTypeLabel(ownerType) {
  if (ownerType === 'teacher') return '教师'
  if (ownerType === 'student') return '学生'
  return '-'
}

export function academicYearOf(year) {
  const value = Number(year)
  if (!value) return ''
  return `${value}-${value + 1}`
}

export function currentAcademicYear() {
  const now = new Date()
  const year = now.getMonth() + 1 >= 9 ? now.getFullYear() : now.getFullYear() - 1
  return `${year}-${year + 1}`
}