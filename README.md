# 专业师生业绩管理系统

面向工程教育 / 专业认证场景的师生业绩管理系统，采用前后端分离架构：

- 后端：Flask 3 + Flask-SQLAlchemy + Flask-JWT-Extended + Flask-Cors + openpyxl（SQLite 存储）
- 前端：Vue 3 + Vite 5 + Element Plus + ECharts + Pinia + Axios

系统支持教师 / 学生 / 管理员三种角色，围绕业绩成果的录入、检索、附件归档、统计分析与数据导入导出形成完整闭环。

## 功能概览

| 模块 | 说明 | 可访问角色 |
| --- | --- | --- |
| 登录 / 个人中心 | JWT 登录、修改资料、修改密码 | 全部 |
| 数据看板 | 关键指标卡片 + 成果类型 / 年度趋势 / 级别分布图表 | 全部（按角色隔离数据） |
| 业绩成果管理 | 成果增删改查、组合筛选、附件上传 / 预览 / 下载 | 全部（非管理员仅本人数据） |
| 统计报表 | 按类型 / 年度 / 级别 / 院系多维统计与图表 | 全部（非管理员仅本人数据） |
| 教师信息管理 | 教师档案维护 | 管理员 |
| 学生信息管理 | 学生档案维护 | 管理员 |
| 账号权限管理 | 建号、角色调整、启停、重置密码 | 管理员 |
| 数据导入导出 | 教师 / 成果 Excel 导入、模板下载、成果与统计报表导出 | 管理员（成果导出对所有角色开放） |

## 目录结构

```
.
├── backend/                 # Flask 后端
│   ├── app.py               # 应用入口（工厂模式 + 全局异常处理）
│   ├── config.py            # 配置（可用 DATABASE_URL 覆盖数据库）
│   ├── models.py            # User / Teacher / Student / Achievement
│   ├── seed.py              # 演示账号与样例数据
│   ├── services.py          # 成果查询构建（含角色数据隔离）
│   ├── auth_utils.py        # 登录校验与角色装饰器
│   ├── routes/              # 各业务蓝图
│   ├── uploads/             # 附件存储目录
│   ├── smoke_test.py        # 接口冒烟测试
│   ├── verify_flows.py      # 业务流程端到端校验（独立临时数据库）
│   └── app.db               # SQLite 数据库（首次启动自动建表并写入演示数据）
├── frontend/                # Vue 3 前端
│   └── src/
│       ├── api/             # 接口封装与 axios 拦截器
│       ├── layout/          # 后台布局与菜单
│       ├── views/           # 页面组件
│       ├── stores/          # Pinia 状态
│       ├── router/          # 路由与登录 / 角色守卫
│       └── utils/           # 文件下载、格式化等工具
├── .venv/                   # 后端 Python 虚拟环境（本地 python -m venv .venv 创建，不入库）
├── assets/app.ico           # 桌面快捷方式图标（由 tools/make_icon.py 生成）
├── tools/
│   ├── make_icon.py         # 纯标准库生成 app.ico
│   └── create_shortcut.ps1  # 在桌面创建一键启动快捷方式
├── start_app.bat            # 一键启动（幂等：已在运行的服务自动跳过，适合快捷方式调用）
├── start_all.bat            # 双击版一键启动（调用 start_app.bat 并停留窗口）
├── create_desktop_shortcut.bat  # 重新生成桌面快捷方式（移动项目后可修复路径）
└── install_frontend.bat     # 前端依赖安装 + 构建（转发到 frontend/install_and_build.bat）
```

## 快速开始

环境要求：Windows + Python 3.11 + Node.js 18+（已在 Python 3.11.9 / Node 22 环境验证）。

### 1. 启动后端

```bat
backend\run_server.bat
```

脚本使用项目根目录下的 `.venv`，默认监听 `http://127.0.0.1:5000`。
首次启动会自动建表并写入演示数据；健康检查：`http://127.0.0.1:5000/api/health`。

若需重新安装依赖：

```bat
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 启动前端

```bat
frontend\run_dev.bat
```

访问 `http://127.0.0.1:5173/`，Vite 已将 `/api` 代理到 `http://127.0.0.1:5000`。

### 3. 一键启动

桌面上已有快捷方式「专业师生业绩管理系统」，双击即可：它会先探测 `5000` 与 `5173`，
只启动尚未运行的服务（两个窗口分别显示后端 / 前端日志），待接口就绪后自动打开浏览器。
启动器本身执行完会自动关闭，不占用窗口。

也可以直接运行项目内的批处理：

```bat
start_all.bat        :: 双击使用：调用 start_app.bat，并在结束后停留显示提示
start_app.bat -n     :: 只启动服务、不打开浏览器（便于脚本化验证）
```

快捷方式丢失或项目文件夹被移动后，重新生成即可（会顺带重建图标）：

```bat
create_desktop_shortcut.bat
```

实现说明：快捷方式指向 `start_app.bat`，工作目录为项目根，窗口最小化运行；
图标来自 `assets/app.ico`（`tools/make_icon.py` 用纯标准库绘制并写出 ICO，
不依赖 Pillow）；`tools/create_shortcut.ps1` 通过 WScript.Shell 写入 `.lnk`。

### 4. 生产构建

```bat
frontend\build.bat            :: 仅构建，产物在 frontend\dist
frontend\install_and_build.bat :: 清空依赖重新安装（npm 镜像）后再构建
```

## 演示账号

| 角色 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| 管理员 | admin | admin123 | 可管理教师、学生、账号、导入导出 |
| 教师 | teacher1 | 123456 | 张伟（计算机学院），仅有本人业绩数据 |
| 教师 | teacher2 / teacher3 | 123456 | 李娜 / 王强 |
| 学生 | student1 / student2 | 123456 | 刘洋 / 陈静 |

演示数据包含 3 名教师、2 名学生、14 条成果记录。

## 统一接口约定

所有接口返回统一信封：

```json
{ "code": 0, "message": "操作成功", "data": {} }
```

- `code === 0` 表示成功，前端 axios 拦截器直接返回 `data`；
- `code !== 0` 时 `message` 为中文提示；HTTP 状态码同时表达语义（400 参数错误、401 未登录、403 越权、404 不存在、413 文件过大、500 服务器异常）；
- 认证方式：`Authorization: Bearer <access_token>`，令牌有效期 12 小时。

主要接口：

```
POST   /api/auth/login                    登录
GET    /api/auth/me                       当前用户
POST   /api/auth/change-password          修改密码
GET    /api/meta/options                  字典项（类型/级别/院系）
GET    /api/achievements/                 成果分页检索（角色隔离）
POST   /api/achievements/                 新增成果
PUT    /api/achievements/{id}             修改成果
DELETE /api/achievements/{id}             删除成果（同时清理附件）
POST   /api/achievements/{id}/attachment  上传附件
GET    /api/achievements/{id}/attachment  下载 / 预览附件（preview=1 为 inline）
GET    /api/teachers/                     教师列表 / /options 下拉
GET    /api/students/                     学生列表 / /options 下拉
GET    /api/users/                        账号列表（管理员）
GET    /api/users/candidates              可关联人员（管理员）
PUT    /api/users/{id}/status             启用 / 禁用账号
POST   /api/users/{id}/reset-password     重置密码
GET    /api/stats/overview                统计概览
GET    /api/stats/breakdown?dimension=    分类 / 年度 / 级别 / 院系分布
POST   /api/import/teachers               Excel 导入教师（自动建号）
POST   /api/import/achievements           Excel 导入成果
GET    /api/import/templates/{kind}       导入模板下载
GET    /api/export/achievements           成果导出（按当前筛选与角色范围）
GET    /api/export/report                 统计报表导出（管理员，5 个工作表）
```

## 自动化校验

后端提供两套脚本，均使用 Flask 测试客户端，无需启动服务：

```bat
backend\run_smoke.bat     :: 冒烟测试，结果写入 backend\smoke.log（末尾 SMOKE_TEST_DONE）
backend\run_verify.bat    :: 业务流程校验，使用独立临时数据库，末尾输出 VERIFY_FLOWS_DONE
```

`smoke_test.py` 覆盖登录、19 个查询接口、成果增改删、附件导出与越权拦截；
`verify_flows.py` 覆盖教师 / 成果导入（含逐行错误提示）、模板下载、Excel 导出内容、报表工作表结构、附件上传-预览-下载-删除、角色数据隔离与账号禁用。

前端构建校验：

```bat
frontend\build.bat        :: 结果见 frontend\build.log，末尾 BUILD_EXIT=0 表示成功
```

## 常见问题

- **端口被占用**：后端改 `backend/app.py` 末尾 `port`，前端改 `frontend/vite.config.js` 的 `server.port` 与代理 `target`。
- **想重置演示数据**：停止服务后删除 `backend/app.db`（可选同时清空 `backend/uploads/`），重新启动即自动重建。
- **使用其他数据库**：设置环境变量 `DATABASE_URL`（如 `mysql+pymysql://user:pwd@host/db`）后启动，需先自行建库。
- **附件类型限制**：pdf、doc(x)、xls(x)、ppt(x)、jpg/png/gif、zip、rar，单文件上限 20MB。
- **修改密码后仍能访问**：JWT 为无状态令牌，旧令牌在有效期内仍可用，重新登录即可获取新令牌。