"""安全工具：登录节流、口令策略、文件名校验。

登录节流使用进程内计数（waitress 多线程下用锁保护）。
单机部署足够；若将来多实例部署，把 `LoginThrottle` 的状态换成 Redis 即可。
"""
import mimetypes
import os
import threading
import time

WEAK_PASSWORDS = {
    '123456', '1234567', '12345678', '123456789', 'password', 'passw0rd',
    'admin123', 'admin888', 'qwerty', 'abc123', '111111', '000000', '888888',
}

# 附件扩展名 → 允许的 MIME 前缀（防止改扩展名上传可执行/脚本文件）
MIME_PREFIX_ALLOWLIST = {
    'pdf': ('application/pdf',),
    'doc': ('application/msword', 'application/octet-stream', 'application/x-ole-storage'),
    'docx': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document',
             'application/zip', 'application/octet-stream'),
    'xls': ('application/vnd.ms-excel', 'application/octet-stream', 'application/x-ole-storage'),
    'xlsx': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
             'application/zip', 'application/octet-stream'),
    'ppt': ('application/vnd.ms-powerpoint', 'application/octet-stream', 'application/x-ole-storage'),
    'pptx': ('application/vnd.openxmlformats-officedocument.presentationml.presentation',
             'application/zip', 'application/octet-stream'),
    'jpg': ('image/jpeg',), 'jpeg': ('image/jpeg',),
    'png': ('image/png',), 'gif': ('image/gif',),
    'bmp': ('image/bmp', 'image/x-ms-bmp'), 'webp': ('image/webp',),
    'zip': ('application/zip', 'application/x-zip-compressed', 'application/octet-stream'),
    'rar': ('application/vnd.rar', 'application/x-rar-compressed', 'application/octet-stream'),
    '7z': ('application/x-7z-compressed', 'application/octet-stream'),
}

# 扩展名 → 附件分类的默认归类（用户仍可手动改）
CATEGORY_HINTS = {
    '证书': '获奖证书',
    '证明': '检索/收录证明',
    '检索': '检索/收录证明',
    '申报': '申报书',
    '立项': '立项/结题材料',
    '结题': '立项/结题材料',
    '照片': '现场照片',
    'photo': '现场照片',
    'img': '现场照片',
}


class LoginThrottle:
    """按登录名统计失败次数，超限后锁定一段时间。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._failures = {}
        self._locked_until = {}

    def _prune(self, key, window, now):
        stamps = [ts for ts in self._failures.get(key, []) if now - ts <= window]
        if stamps:
            self._failures[key] = stamps
        else:
            self._failures.pop(key, None)

    def locked_seconds(self, key):
        with self._lock:
            until = self._locked_until.get(key, 0)
            remaining = int(until - time.time())
            if remaining <= 0:
                self._locked_until.pop(key, None)
                return 0
            return remaining

    def check(self, key, max_attempts, window_seconds):
        """返回 (是否允许登录, 剩余锁定秒数)。"""
        remaining = self.locked_seconds(key)
        if remaining:
            return False, remaining
        with self._lock:
            now = time.time()
            self._prune(key, window_seconds, now)
            if len(self._failures.get(key, [])) >= max_attempts:
                return False, 0
        return True, 0

    def record_failure(self, key, max_attempts, window_seconds, lock_seconds):
        with self._lock:
            now = time.time()
            self._prune(key, window_seconds, now)
            stamps = self._failures.setdefault(key, [])
            stamps.append(now)
            if len(stamps) >= max_attempts:
                self._locked_until[key] = now + lock_seconds
                self._failures[key] = []
        return self.locked_seconds(key)

    def reset(self, key):
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset_all(self):
        """清空全部节流记录（测试或运维解锁时使用）。"""
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()

    def snapshot(self):
        """返回节流状态：汇总计数 + 每个账号的明细（供系统维护页展示）。"""
        with self._lock:
            now = time.time()
            accounts = {}
            for key, stamps in self._failures.items():
                accounts[key] = {'recent_failures': len(stamps), 'locked_seconds': 0}
            for key, until in self._locked_until.items():
                entry = accounts.setdefault(key, {'recent_failures': 0, 'locked_seconds': 0})
                entry['locked_seconds'] = max(int(until - now), 0)
            return {
                'tracked_accounts': len(accounts),
                'locked_accounts': len(self._locked_until),
                'accounts': accounts,
            }


login_throttle = LoginThrottle()


def validate_password(password, min_length=6, strength_check=False):
    """返回 (是否通过, 错误提示)。"""
    if not password:
        return False, '请输入密码'
    if len(password) < min_length:
        return False, f'密码长度不能少于 {min_length} 位'
    if len(password) > 128:
        return False, '密码长度不能超过 128 位'
    if strength_check:
        lowered = password.strip().lower()
        if lowered in WEAK_PASSWORDS:
            return False, '密码过于简单，请使用更复杂的密码'
        kinds = sum([
            any(ch.islower() for ch in password),
            any(ch.isupper() for ch in password),
            any(ch.isdigit() for ch in password),
            any(not ch.isalnum() for ch in password),
        ])
        if kinds < 2:
            return False, '密码需至少包含字母、数字、符号中的两类'
    return True, ''


def normalize_text(value):
    """清理全角空格、首尾空白与零宽字符，避免同一含义被统计成多项。"""
    if value is None:
        return ''
    text_value = str(value)
    for ch in ('\u3000', '\u200b', '\ufeff'):
        text_value = text_value.replace(ch, ' ')
    return ' '.join(text_value.split()).strip()


def safe_filename(filename):
    name = str(filename or '').replace('\\', '/').split('/')[-1]
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, '_')
    name = name.replace('..', '').strip().strip('.')
    if not name:
        name = 'attachment'
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                'LPT1', 'LPT2', 'LPT3'}
    stem = name.rsplit('.', 1)[0].upper()
    if stem in reserved:
        name = f'_{name}'
    return name[:180]


def file_extension(filename):
    if filename is None or '.' not in str(filename):
        return ''
    return str(filename).rsplit('.', 1)[1].lower()


def allowed_file(filename, allowed_extensions):
    return file_extension(filename) in set(allowed_extensions)


def mime_allowed(filename, content_type):
    """扩展名与浏览器上报的 MIME 双向校验；MIME 缺失时按扩展名放行。"""
    ext = file_extension(filename)
    allowed = MIME_PREFIX_ALLOWLIST.get(ext)
    if not allowed:
        return False
    if not content_type:
        return True
    return any(content_type.startswith(prefix) for prefix in allowed)


def guess_mime(filename):
    guessed, _encoding = mimetypes.guess_type(str(filename or ''))
    return guessed or 'application/octet-stream'


def guess_attachment_category(filename):
    lowered = str(filename or '').lower()
    for keyword, category in CATEGORY_HINTS.items():
        if keyword.lower() in lowered:
            return category
    return '其他'


def build_relative_path(app_config, owner_type, owner_id, achievement_id, filename):
    """支撑材料分类存储路径：uploads/<学年>/<owner_type>_<owner_id>/<achievement_id>/<文件>。

    相比原来的平铺目录，便于按学年+人员直接定位与整目录打包。
    """
    from datetime import datetime
    year = datetime.now().year
    academic_year = f'{year}-{year + 1}'
    relative_dir = os.path.join(academic_year, f'{owner_type}_{owner_id}', str(achievement_id))
    return relative_dir, safe_filename(filename)