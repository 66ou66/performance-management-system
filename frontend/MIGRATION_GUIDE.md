# 前端迁移指南（Element Plus → shadcn-vue）

本文件是「专业师生业绩管理系统」前端 UI 迁移的**唯一约定来源**。迁移页面时请严格遵守。

## 项目位置
`C:\Users\www32\Desktop\项目文件夹\业绩管理系统\frontend`

## 铁律
1. **只改 `.vue` 视图文件**。严禁改动：`src/api/**`、`src/stores/**`、`src/router/**`、`src/utils/**`、`src/components/ui/**`、`src/components/EChart.vue`。
2. **禁止再使用任何 `element-plus` 或 `@element-plus/icons-vue` 导入**。全部换成 shadcn-vue + lucide-vue-next + vue-sonner。
3. 保留原有 `<script setup>` 的**业务逻辑不变**：数据加载、接口调用、分页、状态流转的语义完全一致，只替换 UI 层。
4. 弹提示用 `import { toast } from 'vue-sonner'`（`toast.success/error/warning/info`）。`ElMessage`→`toast`，`ElMessageBox.confirm/prompt`→用共享的 `ConfirmDialog`（确认）或 `Dialog`+输入（需要用户输入时）。

## 参考范例（先读这三个）
- `src/views/TeacherListView.vue` —— **CRUD 列表页标准写法**（筛选 + 表格 + 分页 + 新增/编辑弹窗 + 删除确认 + 详情弹窗）。
- `src/views/DashboardView.vue` —— 图表卡片 + 统计卡 + 带 Badge 的表格。
- `src/layout/AppLayout.vue` —— 下拉菜单、Alert、退出确认。

## 共享组件
- 分页：`import AppPagination from '../components/AppPagination.vue'`
  `<AppPagination :total="total" :page="page" :page-size="pageSize" @change="onPageChange" />`
  `onPageChange({ page, pageSize })` 里 `page.value = page; pageSize.value = pageSize; loadList()`。
- 确认框：`import ConfirmDialog from '../components/ConfirmDialog.vue'`
  见 TeacherListView 的 `askConfirm`/`onConfirm` 用法（一个 reactive 状态 + handler 函数）。

## shadcn-vue 组件导入路径与要点
全部从 `@/components/ui/<name>` 导入。已有组件：button, card, input, label, textarea, select, dialog, dropdown-menu, table, badge, avatar, tabs, separator, skeleton, tooltip, switch, checkbox, radio-group, alert, alert-dialog, popover, sheet, sonner。

- Button：`import { Button } from '@/components/ui/button'`；`variant` = default/destructive/outline/secondary/ghost/link；`size` = default/sm/lg/icon。表单提交用 `type="submit"` 或 `@click`。
- Input：`v-model` 可用；`type/placeholder/maxlength/disabled` 等自动透传到 input。
- Textarea：同 Input。
- Label：`<Label>名字</Label>`。
- Select：**value 必须是字符串**。写法：
  ```vue
  <Select v-model="val">
    <SelectTrigger class="w-[120px]"><SelectValue placeholder="全部" /></SelectTrigger>
    <SelectContent>
      <SelectItem value="__all__">全部</SelectItem>
      <SelectItem v-for="i in list" :key="i" :value="String(i)">{{ i }}</SelectItem>
    </SelectContent>
  </Select>
  ```
  用 `__all__` 作「全部/不筛选」哨兵值；`buildParams()` 里跳过空串和 `__all__`。
- Table：`import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableEmpty } from '@/components/ui/table'`；空态用 `<TableEmpty :colspan="列数">暂无数据</TableEmpty>`。
- Dialog：`import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'`；受控用 `<Dialog v-model:open="visible">`。
- Badge：`variant` = default/secondary/destructive/outline。
- Switch：`:checked="x"` + `@update:checked="x = $event"`。
- Checkbox 用 `Checkbox`；RadioGroup 用 `RadioGroup`/`RadioGroupItem`。
- Separator：`import { Separator } from '@/components/ui/separator'`。
- Tabs：`import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'`。
- Alert：`import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'`。

## 图标（lucide-vue-next）
`import { Plus, Search, RotateCcw, Trash2, Pencil, Eye, Upload, Download, RefreshCw, MoreHorizontal, FileText, Users, UserRound, GraduationCap, BarChart3, Settings, LogOut, Check, X, ChevronDown } from 'lucide-vue-next'`。图标一律 `<Xxx class="size-4" />`。

## 状态/角色 Badge 配色（替换 el-tag 的 type）
```js
const statusBadgeClass = {
  draft: 'text-zinc-500',
  pending: 'text-amber-600',
  approved: 'text-emerald-600',
  rejected: 'text-destructive'
}
```
`roleLabel(status)` 从 `@/utils/file`（`../utils/file`）导入。角色配色的 map 参考 AppLayout.vue 里的 `roleBadgeClass`。

## 页面骨架（统一）
```vue
<div class="space-y-4 p-6">
  <!-- 页头：标题+副标题 左，操作按钮 右 -->
  <div class="flex flex-wrap items-start justify-between gap-3">…</div>
  <!-- 筛选卡片 -->
  <div class="rounded-xl border bg-white p-4 shadow-sm">…</div>
  <!-- 表格卡片 -->
  <div class="rounded-xl border bg-white shadow-sm">…</div>
</div>
```
栅格用 `grid gap-4 md:grid-cols-2` 等 Tailwind 类，不要用 el-row/el-col。

## 校验约定
原 el-form 的 rules 校验，改为 `handleSubmit` 里手写 `validate()`：非空校验失败就 `toast.error(...)` 并 `return`；邮箱用 `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`。

## 完成自查
迁移后该文件内 `grep element-plus` 应为 0 结果；`npm run build` 必须通过（委托结束后由主流程统一跑）。