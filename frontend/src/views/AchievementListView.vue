<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">业绩成果管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          教师教学/科研/指导学生成果与学生竞赛、论文、专利、软著等业绩的录入与多条件检索
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button variant="outline" @click="router.push('/trash')"><Trash2 class="size-4" /> 回收站</Button>
        <Button variant="outline" @click="handleExport"><Download class="size-4" /> 导出当前结果</Button>
        <Button @click="openCreate"><Plus class="size-4" /> 新增成果</Button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="rounded-xl border bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">关键词</Label>
          <Input v-model="filters.keyword" placeholder="成果名称/描述/级别" class="w-[180px]" @keyup.enter="handleSearch" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">所属人</Label>
          <Input v-model="filters.owner_name" placeholder="姓名" class="w-[110px]" @keyup.enter="handleSearch" />
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">类型</Label>
          <Select v-model="filters.category">
            <SelectTrigger class="w-[140px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in allCategories" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">级别</Label>
          <Select v-model="filters.level">
            <SelectTrigger class="w-[120px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in levelOptions" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">年份</Label>
          <Select v-model="filters.year">
            <SelectTrigger class="w-[100px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in years" :key="item" :value="String(item)">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">学年</Label>
          <Select v-model="filters.academic_year">
            <SelectTrigger class="w-[120px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in academicYears" :key="item" :value="String(item)">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div v-if="isElevated" class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">人员类型</Label>
          <Select v-model="filters.owner_type">
            <SelectTrigger class="w-[100px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem value="teacher">教师</SelectItem>
              <SelectItem value="student">学生</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">院系</Label>
          <Select v-model="filters.department">
            <SelectTrigger class="w-[140px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in departments" :key="item" :value="item">{{ item }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">状态</Label>
          <Select v-model="filters.status">
            <SelectTrigger class="w-[110px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in statuses" :key="item.value" :value="item.value">{{ item.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">材料</Label>
          <Select v-model="filters.has_attachment">
            <SelectTrigger class="w-[110px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem value="1">已归档</SelectItem>
              <SelectItem value="0">缺材料</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div v-if="isElevated" class="space-y-1.5">
          <Label class="text-xs text-muted-foreground">指标点</Label>
          <Select v-model="filters.indicator_id">
            <SelectTrigger class="w-[160px]"><SelectValue placeholder="全部" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">全部</SelectItem>
              <SelectItem v-for="item in indicators" :key="item.id" :value="String(item.id)">{{ item.code }} {{ item.name }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="flex gap-2">
          <Button @click="handleSearch"><Search class="size-4" /> 查询</Button>
          <Button variant="outline" @click="handleReset"><RotateCcw class="size-4" /> 重置</Button>
        </div>
      </div>

      <div v-if="selectedIds.length" class="mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
        <span class="text-sm font-medium text-blue-700">已选择 {{ selectedIds.length }} 条</span>
        <Button size="sm" variant="outline" @click="batchSetLevel">批量设级别</Button>
        <Button size="sm" variant="outline" @click="batchAddIndicators">批量关联指标点</Button>
        <Button v-if="isElevated" size="sm" variant="outline" @click="batchSetStatus">批量改状态</Button>
        <Button size="sm" variant="destructive" @click="batchDelete">批量移入回收站</Button>
        <Button size="sm" variant="ghost" @click="selectedIds = []">取消选择</Button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="rounded-xl border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[44px]">
              <Checkbox :checked="allSelected" @update:checked="toggleAll" />
            </TableHead>
            <TableHead>成果名称</TableHead>
            <TableHead class="w-[150px]">所属人</TableHead>
            <TableHead class="w-[130px]">院系</TableHead>
            <TableHead class="w-[115px]">成果类型</TableHead>
            <TableHead class="w-[110px]">级别</TableHead>
            <TableHead class="w-[90px]">年份</TableHead>
            <TableHead class="w-[100px]">状态</TableHead>
            <TableHead class="w-[120px]">指标点</TableHead>
            <TableHead class="w-[165px]">更新时间</TableHead>
            <TableHead class="w-[260px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="row in items" :key="row.id">
            <TableCell>
              <Checkbox :checked="selectedIds.includes(row.id)" @update:checked="toggleSelect(row.id)" />
            </TableCell>
            <TableCell>
              <span class="max-w-[240px] truncate font-medium">{{ row.title }}</span>
              <Badge v-if="!row.attachment_count" variant="secondary" class="ml-1.5 text-destructive">缺材料</Badge>
              <Badge v-else variant="secondary" class="ml-1.5 text-emerald-600">{{ row.attachment_count }} 份材料</Badge>
            </TableCell>
            <TableCell>
              <button type="button" class="font-medium text-blue-600 hover:underline" @click="filterByOwner(row.owner_name)">
                {{ row.owner_name }}
              </button>
              <Badge variant="outline" class="ml-1.5 text-muted-foreground">{{ ownerTypeLabel(row.owner_type) }}</Badge>
            </TableCell>
            <TableCell class="max-w-[130px] truncate text-muted-foreground">{{ row.owner_department || '-' }}</TableCell>
            <TableCell>{{ row.category }}</TableCell>
            <TableCell>
              <Badge v-if="row.level" variant="secondary" :class="levelBadgeClass[row.level] || 'text-muted-foreground'">{{ row.level }}</Badge>
              <span v-else class="text-muted-foreground">-</span>
            </TableCell>
            <TableCell>{{ row.year }}</TableCell>
            <TableCell>
              <Badge variant="secondary" :class="statusBadgeClass[row.status] || 'text-muted-foreground'">{{ statusLabel(row.status) }}</Badge>
            </TableCell>
            <TableCell class="text-muted-foreground">
              {{ row.indicators && row.indicators.length ? row.indicators.map((item) => item.code).join('、') : '未关联' }}
            </TableCell>
            <TableCell class="text-muted-foreground">{{ row.updated_at }}</TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-1">
                <Button variant="ghost" size="sm" @click="openDetail(row)">查看</Button>
                <Button v-if="canEditRow(row)" variant="ghost" size="sm" @click="openEdit(row)">编辑</Button>
                <Button variant="ghost" size="sm" @click="openAttachments(row)">材料</Button>
                <DropdownMenu>
                  <DropdownMenuTrigger as-child>
                    <Button variant="ghost" size="sm">更多 <ChevronDown class="size-4" /></Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" class="w-40">
                    <DropdownMenuItem :disabled="row.status === 'approved'" @click="handleSubmitReview(row)">提交审核</DropdownMenuItem>
                    <DropdownMenuItem v-if="isElevated" @click="handleReview(row, 'approve', '材料齐全，审核通过')">审核通过</DropdownMenuItem>
                    <DropdownMenuItem v-if="isElevated" @click="handleReject(row)">审核驳回</DropdownMenuItem>
                    <DropdownMenuItem v-if="canEditRow(row)" @click="openIndicators(row)">关联指标点</DropdownMenuItem>
                    <DropdownMenuSeparator v-if="canEditRow(row)" />
                    <DropdownMenuItem v-if="canEditRow(row)" class="text-destructive focus:text-destructive" @click="handleDelete(row)">移入回收站</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </TableCell>
          </TableRow>
          <TableEmpty v-if="!items.length" :colspan="11">暂无成果数据</TableEmpty>
        </TableBody>
      </Table>

      <div class="border-t px-4 py-3">
        <AppPagination :total="total" :page="page" :page-size="pageSize" :page-sizes="[10, 20, 50, 100]" @change="onPageChange" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="max-h-[90vh] overflow-y-auto sm:max-w-[680px]">
        <DialogHeader>
          <DialogTitle>{{ dialogMode === 'create' ? '新增业绩成果' : '编辑业绩成果' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-3.5">
          <div v-if="isAdmin" class="grid gap-1.5">
            <Label>人员类型 <span class="text-destructive">*</span></Label>
            <div class="inline-flex items-center gap-1 rounded-lg border bg-muted p-1">
              <Button :variant="form.owner_type === 'teacher' ? 'default' : 'ghost'" size="sm" @click="handleOwnerTypeChange('teacher')">教师</Button>
              <Button :variant="form.owner_type === 'student' ? 'default' : 'ghost'" size="sm" @click="handleOwnerTypeChange('student')">学生</Button>
            </div>
          </div>
          <div v-if="isAdmin" class="grid gap-1.5">
            <Label>所属人 <span class="text-destructive">*</span></Label>
            <Select :model-value="form.owner_id == null ? '' : String(form.owner_id)" @update:model-value="form.owner_id = $event ? Number($event) : null">
              <SelectTrigger><SelectValue placeholder="请选择所属人" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in ownerOptions" :key="item.id" :value="String(item.id)">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div v-else class="grid gap-1.5">
            <Label>所属人</Label>
            <Input :model-value="userStore.displayName" disabled />
          </div>
          <div class="grid gap-1.5">
            <Label>成果类型 <span class="text-destructive">*</span></Label>
            <Select v-model="form.category">
              <SelectTrigger><SelectValue placeholder="请选择成果类型" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in categoryOptions" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-1.5">
            <Label>成果名称 <span class="text-destructive">*</span></Label>
            <Input v-model="form.title" maxlength="255" placeholder="请输入成果名称" />
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="grid gap-1.5">
              <Label>年份 <span class="text-destructive">*</span></Label>
              <Select v-model="form.year" @update:model-value="handleYearChange(String($event))">
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="item in yearOptions" :key="item" :value="String(item)">{{ item }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="grid gap-1.5">
              <Label>学年</Label>
              <Input v-model="form.academic_year" placeholder="如 2024-2025" />
            </div>
            <div class="grid gap-1.5">
              <Label>级别</Label>
              <Select v-model="form.level">
                <SelectTrigger><SelectValue placeholder="请选择级别" /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="item in formLevels" :key="item" :value="item">{{ item }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="grid gap-1.5">
              <Label>完成人排序</Label>
              <Select v-model="form.role_rank">
                <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="item in roleRanks" :key="item" :value="item">{{ item }}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div v-if="canPickAdvisor" class="grid gap-1.5">
            <Label>指导教师</Label>
            <Select :model-value="form.advisor_id == null ? '' : String(form.advisor_id)" @update:model-value="form.advisor_id = $event ? Number($event) : null">
              <SelectTrigger><SelectValue placeholder="请选择指导教师" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in advisorOptions" :key="item.id" :value="String(item.id)">{{ item.name }}（{{ item.department || '未设院系' }}）</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <template v-if="formFields.length">
            <Separator />
            <div class="text-sm font-medium">{{ form.category }}专有字段</div>
            <div class="grid gap-4 sm:grid-cols-2">
              <div v-for="field in formFields" :key="field.key" :class="field.type === 'textarea' ? 'grid gap-1.5 sm:col-span-2' : 'grid gap-1.5'">
                <Label>{{ field.label }}</Label>
                <Select v-if="field.type === 'select'" v-model="form.extra[field.key]">
                  <SelectTrigger><SelectValue placeholder="请选择" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="item in field.options || []" :key="item" :value="item">{{ item }}</SelectItem>
                  </SelectContent>
                </Select>
                <Input v-else-if="field.type === 'number'" v-model.number="form.extra[field.key]" type="number" />
                <Input v-else-if="field.type === 'date'" v-model="form.extra[field.key]" type="date" />
                <Textarea v-else-if="field.type === 'textarea'" v-model="form.extra[field.key]" rows="2" :maxlength="field.maxlength || 200" />
                <Input v-else v-model="form.extra[field.key]" :maxlength="field.maxlength || 200" :placeholder="`请输入${field.label}`" />
              </div>
            </div>
          </template>

          <div class="grid gap-1.5">
            <Label>认证指标点</Label>
            <div class="max-h-[160px] space-y-1 overflow-auto rounded-md border p-2">
              <label v-for="item in indicators" :key="item.id" class="flex cursor-pointer items-center gap-2 rounded px-2 py-1 hover:bg-muted">
                <Checkbox :checked="form.indicator_ids.includes(item.id)" @update:checked="toggleIndicator(item.id)" />
                <span class="text-sm">{{ item.code }} {{ item.name }}</span>
              </label>
              <p v-if="!indicators.length" class="px-2 py-1 text-sm text-muted-foreground">暂无指标点</p>
            </div>
          </div>
          <div class="grid gap-1.5">
            <Label>成果描述</Label>
            <Textarea v-model="form.description" rows="4" maxlength="2000" placeholder="请填写成果的简要说明" />
          </div>
          <div v-if="isElevated" class="grid gap-1.5">
            <Label>审核状态</Label>
            <Select v-model="form.status">
              <SelectTrigger><SelectValue placeholder="不修改" /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in statuses" :key="item.value" :value="item.value">{{ item.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="dialogVisible = false">取消</Button>
          <Button :disabled="saving" @click="handleSubmit">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 支撑材料弹窗 -->
    <Dialog v-model:open="attachmentVisible">
      <DialogContent class="sm:max-w-[720px]">
        <DialogHeader>
          <DialogTitle>支撑材料管理</DialogTitle>
        </DialogHeader>
        <template v-if="currentRow">
          <div class="text-sm text-muted-foreground">
            成果：<span class="font-medium text-foreground">{{ currentRow.title }}</span>（{{ currentRow.category }}）—— 共 {{ currentRow.attachment_count || 0 }} 份材料
          </div>
          <div v-if="canEditRow(currentRow)" class="flex flex-wrap items-center gap-3">
            <Select v-model="uploadCategory">
              <SelectTrigger class="w-[180px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem v-for="item in attachmentCategories" :key="item" :value="item">{{ item }}</SelectItem>
              </SelectContent>
            </Select>
            <input
              ref="fileInputRef"
              type="file"
              multiple
              class="hidden"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.gif,.bmp,.webp,.zip,.rar,.7z"
              @change="onFilesSelected"
            />
            <Button @click="fileInputRef.click()"><Upload class="size-4" /> 上传材料</Button>
            <span class="text-xs text-muted-foreground">单条成果最多 20 份，单个文件不超过 20MB</span>
          </div>
          <p v-else class="text-sm text-muted-foreground">当前角色仅可查看与下载支撑材料。</p>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>文件名</TableHead>
                <TableHead class="w-[140px]">材料分类</TableHead>
                <TableHead class="w-[90px]">大小</TableHead>
                <TableHead class="w-[160px]">上传时间</TableHead>
                <TableHead class="w-[150px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="row in currentRow.attachments || []" :key="row.id">
                <TableCell class="max-w-[200px] truncate font-medium">{{ row.original_name }}</TableCell>
                <TableCell>{{ row.category }}</TableCell>
                <TableCell class="text-muted-foreground">{{ row.size_text }}</TableCell>
                <TableCell class="text-muted-foreground">{{ row.uploaded_at }}</TableCell>
                <TableCell class="text-right">
                  <div class="flex justify-end gap-1">
                    <Button variant="ghost" size="sm" @click="downloadAttachment(row, false)">下载</Button>
                    <Button variant="ghost" size="sm" @click="downloadAttachment(row, true)">预览</Button>
                    <Button v-if="canEditRow(currentRow)" variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="removeAttachment(row)">删除</Button>
                  </div>
                </TableCell>
              </TableRow>
              <TableEmpty v-if="!(currentRow.attachments || []).length" :colspan="5">暂无支撑材料</TableEmpty>
            </TableBody>
          </Table>
        </template>
      </DialogContent>
    </Dialog>

    <!-- 详情弹窗 -->
    <Dialog v-model:open="drawerVisible">
      <DialogContent class="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>成果详情</DialogTitle>
        </DialogHeader>
        <template v-if="detail">
          <dl class="space-y-2.5 text-sm">
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">成果名称</dt><dd class="font-medium">{{ detail.title }}</dd></div>
            <div class="flex gap-2">
              <dt class="w-24 shrink-0 text-muted-foreground">审核状态</dt>
              <dd>
                <Badge variant="secondary" :class="statusBadgeClass[detail.status] || 'text-muted-foreground'">{{ statusLabel(detail.status) }}</Badge>
                <span v-if="detail.review_comment" class="ml-1 text-xs text-muted-foreground">（{{ detail.review_comment }}）</span>
              </dd>
            </div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">所属人</dt><dd>{{ detail.owner_name }}（{{ ownerTypeLabel(detail.owner_type) }}）</dd></div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">所属院系</dt><dd>{{ detail.owner_department || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">成果类型</dt><dd>{{ detail.category }}</dd></div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">级别</dt><dd>{{ detail.level || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">年份/学年</dt><dd>{{ detail.year || '-' }} / {{ detail.academic_year || '-' }}</dd></div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">完成人排序</dt><dd>{{ detail.role_rank || '-' }}</dd></div>
            <div v-if="detail.advisor_name" class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">指导教师</dt><dd>{{ detail.advisor_name }}</dd></div>
            <div class="flex gap-2">
              <dt class="w-24 shrink-0 text-muted-foreground">认证指标点</dt>
              <dd>
                <div v-if="detail.indicators && detail.indicators.length" class="flex flex-wrap gap-1.5">
                  <Badge v-for="item in detail.indicators" :key="item.id" variant="secondary">{{ item.code }} {{ item.name }}</Badge>
                </div>
                <span v-else class="text-muted-foreground">未关联</span>
              </dd>
            </div>
            <div class="flex gap-2">
              <dt class="w-24 shrink-0 text-muted-foreground">支撑材料</dt>
              <dd class="flex-1">
                <div v-if="detail.attachments && detail.attachments.length" class="space-y-1.5">
                  <div v-for="item in detail.attachments" :key="item.id" class="flex items-center gap-2">
                    <Badge variant="outline">{{ item.category }}</Badge>
                    <span class="min-w-0 flex-1 truncate">{{ item.original_name }}</span>
                    <Button variant="ghost" size="sm" @click="downloadAttachment(item, true)">预览</Button>
                    <Button variant="ghost" size="sm" @click="downloadAttachment(item, false)">下载</Button>
                  </div>
                </div>
                <span v-else class="text-muted-foreground">暂无支撑材料</span>
              </dd>
            </div>
            <div class="flex gap-2">
              <dt class="w-24 shrink-0 text-muted-foreground">专有字段</dt>
              <dd>
                <div v-if="extraEntries(detail).length">
                  <div v-for="entry in extraEntries(detail)" :key="entry.label">{{ entry.label }}：{{ entry.value }}</div>
                </div>
                <span v-else class="text-muted-foreground">暂无</span>
              </dd>
            </div>
            <div class="flex gap-2">
              <dt class="w-24 shrink-0 text-muted-foreground">成果描述</dt>
              <dd class="whitespace-pre-wrap">{{ detail.description || '暂无描述' }}</dd>
            </div>
            <div class="flex gap-2"><dt class="w-24 shrink-0 text-muted-foreground">录入/更新</dt><dd class="text-muted-foreground">{{ detail.created_at }} / {{ detail.updated_at }}</dd></div>
          </dl>
          <DialogFooter>
            <Button v-if="canEditRow(detail)" @click="openEdit(detail)">编辑</Button>
            <Button variant="outline" @click="openAttachments(detail)">
              {{ canEditRow(detail) ? '管理支撑材料' : '查看支撑材料' }}
            </Button>
          </DialogFooter>
        </template>
      </DialogContent>
    </Dialog>

    <!-- 输入型弹窗 -->
    <Dialog v-model:open="promptState.open">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ promptState.title }}</DialogTitle>
          <DialogDescription v-if="promptState.description">{{ promptState.description }}</DialogDescription>
        </DialogHeader>
        <Textarea v-if="promptState.textarea" v-model="promptState.value" rows="3" :placeholder="promptState.placeholder" />
        <Input v-else v-model="promptState.value" :placeholder="promptState.placeholder" />
        <DialogFooter>
          <Button variant="outline" @click="promptState.open = false">取消</Button>
          <Button @click="confirmPrompt">{{ promptState.confirmText }}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 确认弹窗 -->
    <ConfirmDialog
      v-model:open="confirmState.open"
      :title="confirmState.title"
      :description="confirmState.description"
      :confirm-text="confirmState.confirmText"
      :danger="confirmState.danger"
      @confirm="onConfirm"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { ChevronDown, Download, Plus, RotateCcw, Search, Trash2, Upload } from 'lucide-vue-next'
import AppPagination from '../components/AppPagination.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Table, TableBody, TableCell, TableEmpty, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { achievementApi, ioApi, metaApi, studentApi, teacherApi } from '../api'
import { useUserStore } from '../stores/user'
import { academicYearOf, openBlob, ownerTypeLabel, saveBlob, statusLabel } from '../utils/file'

const statusBadgeClass = {
  draft: 'text-zinc-500',
  pending: 'text-amber-600',
  approved: 'text-emerald-600',
  rejected: 'text-destructive'
}

const levelBadgeClass = {
  国家级: 'text-destructive',
  国际级: 'text-destructive',
  省部级: 'text-amber-600',
  省级: 'text-amber-600',
  市厅级: 'text-blue-600',
  校级: 'text-emerald-600',
  院级: 'text-zinc-500',
  其他: 'text-zinc-500'
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')
const isElevated = computed(() => userStore.isElevated)
const canEditRow = (row) => {
  if (!row) return false
  if (isAdmin.value) return true
  if (isElevated.value) return false
  return row.owner_type === userStore.role
}

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const saving = ref(false)
const selectedIds = ref([])
const sort = ref({ prop: '-year', order: null })

const allCategories = ref([])
const teacherCategories = ref([])
const studentCategories = ref([])
const levelsByCategory = ref({})
const levels = ref([])
const levelOptions = computed(() => (filters.category && filters.category !== '__all__' ? levelsByCategory.value[filters.category] || levels.value : levels.value))
const years = ref([])
const academicYears = ref([])
const departments = ref([])
const indicators = ref([])
const fieldTemplates = ref({})
const awardRanks = ref([])
const roleRanks = ref([])
const statuses = ref([])
const attachmentCategories = ref([])

const filters = reactive({
  keyword: '',
  owner_name: '',
  category: '__all__',
  level: '__all__',
  year: '__all__',
  academic_year: '__all__',
  owner_type: '__all__',
  department: '__all__',
  status: '__all__',
  has_attachment: '__all__',
  indicator_id: '__all__'
})

const dialogVisible = ref(false)
const dialogMode = ref('create')
const ownerOptions = ref([])
const advisorOptions = ref([])
const drawerVisible = ref(false)
const detail = ref(null)

const attachmentVisible = ref(false)
const currentRow = ref(null)
const uploadCategory = ref('其他')
const fileInputRef = ref(null)

const allSelected = computed(() => items.value.length > 0 && selectedIds.value.length === items.value.length)

const confirmState = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  danger: false,
  handler: null
})

const promptState = reactive({
  open: false,
  title: '',
  description: '',
  value: '',
  textarea: false,
  placeholder: '',
  confirmText: '确认',
  validate: null,
  handler: null
})

function emptyForm() {
  return {
    id: null,
    owner_type: isAdmin.value ? 'teacher' : userStore.role,
    owner_id: null,
    category: '',
    title: '',
    year: String(new Date().getFullYear()),
    academic_year: academicYearOf(new Date().getFullYear()),
    level: '',
    role_rank: '',
    advisor_id: null,
    indicator_ids: [],
    extra: {},
    description: '',
    status: ''
  }
}

const form = reactive(emptyForm())
const yearOptions = computed(() => {
  const current = new Date().getFullYear() + 1
  const list = []
  for (let year = current; year >= 1990; year -= 1) list.push(year)
  return list
})
const categoryOptions = computed(() => {
  if (form.owner_type === 'teacher') return teacherCategories.value
  if (form.owner_type === 'student') return studentCategories.value
  return allCategories.value
})
const formLevels = computed(() => {
  if (!form.category) return levels.value
  return levelsByCategory.value[form.category] || levels.value
})
const formFields = computed(() => fieldTemplates.value[form.category] || [])
const canPickAdvisor = computed(() => {
  const ownerType = isAdmin.value ? form.owner_type : userStore.role
  return ownerType === 'student'
})

async function loadMeta() {
  try {
    const data = await metaApi.options()
    allCategories.value = data.all_categories || []
    teacherCategories.value = data.teacher_categories || []
    studentCategories.value = data.student_categories || []
    levels.value = data.levels || []
    levelsByCategory.value = data.levels_by_category || {}
    years.value = data.years || []
    academicYears.value = data.academic_years || []
    departments.value = (data.dicts && data.dicts.department) || data.departments || []
    indicators.value = data.indicators || []
    fieldTemplates.value = data.field_templates || {}
    awardRanks.value = data.award_ranks || []
    roleRanks.value = data.role_ranks || []
    statuses.value = data.statuses || []
    attachmentCategories.value = data.attachment_categories || ['其他']
    if (!attachmentCategories.value.includes('其他')) attachmentCategories.value.push('其他')
  } catch (err) {
    // 统一错误处理
  }
}

function applyQuery() {
  const query = route.query || {}
  const queryToFilter = { ...query }
  if (queryToFilter.year) filters.year = String(queryToFilter.year)
  if (queryToFilter.keyword) filters.keyword = String(queryToFilter.keyword)
  if (queryToFilter.owner_name) filters.owner_name = String(queryToFilter.owner_name)
  if (queryToFilter.category) filters.category = String(queryToFilter.category)
  if (queryToFilter.level) filters.level = String(queryToFilter.level)
  if (queryToFilter.academic_year) filters.academic_year = String(queryToFilter.academic_year)
  if (queryToFilter.owner_type) filters.owner_type = String(queryToFilter.owner_type)
  if (queryToFilter.department) filters.department = String(queryToFilter.department)
  if (queryToFilter.status) filters.status = String(queryToFilter.status)
  if (queryToFilter.has_attachment) filters.has_attachment = String(queryToFilter.has_attachment)
  if (queryToFilter.indicator_id) {
    filters.indicator_id = String(queryToFilter.indicator_id)
  } else if (queryToFilter.owner_name) {
    filters.keyword = ''
  }
  if (query.page) page.value = Number(query.page) || 1
  if (query.page_size) pageSize.value = Number(query.page_size) || 10
}

function syncQuery() {
  const query = {}
  Object.keys(filters).forEach((key) => {
    if (filters[key] !== '' && filters[key] !== '__all__' && filters[key] !== null && filters[key] !== undefined) {
      query[key] = filters[key]
    }
  })
  if (page.value > 1) query.page = String(page.value)
  if (pageSize.value !== 10) query.page_size = String(pageSize.value)
  if (sort.value.prop) query.sort = sort.value.prop
  router.replace({ path: '/achievements', query }).catch(() => {})
}

function buildParams() {
  const params = { page: page.value, page_size: pageSize.value }
  Object.keys(filters).forEach((key) => {
    const value = filters[key]
    if (value !== '' && value !== '__all__' && value !== null && value !== undefined) params[key] = value
  })
  if (filters.indicator_id && filters.indicator_id !== '__all__') params.indicator_id = Number(filters.indicator_id)
  if (sort.value.prop) params.sort = sort.value.prop
  return params
}

async function loadList() {
  loading.value = true
  try {
    const data = await achievementApi.list(buildParams())
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onPageChange({ page: p, pageSize: ps }) {
  page.value = p
  pageSize.value = ps
  syncQuery()
  loadList()
}

function handleSearch() {
  page.value = 1
  syncQuery()
  loadList()
}

function handleReset() {
  Object.keys(filters).forEach((key) => {
    filters[key] = ''
  })
  filters.category = '__all__'
  filters.level = '__all__'
  filters.year = '__all__'
  filters.academic_year = '__all__'
  filters.owner_type = '__all__'
  filters.department = '__all__'
  filters.status = '__all__'
  filters.has_attachment = '__all__'
  filters.indicator_id = '__all__'
  sort.value = { prop: '-year', order: null }
  page.value = 1
  syncQuery()
  loadList()
}

function toggleSelect(id) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}

function toggleAll() {
  if (allSelected.value) selectedIds.value = []
  else selectedIds.value = items.value.map((row) => row.id)
}

function toggleIndicator(id) {
  const i = form.indicator_ids.indexOf(id)
  if (i >= 0) form.indicator_ids.splice(i, 1)
  else form.indicator_ids.push(id)
}

function filterByOwner(name) {
  filters.owner_name = name
  filters.keyword = ''
  page.value = 1
  syncQuery()
  loadList()
}

async function loadOwnerOptions(ownerType) {
  ownerOptions.value = []
  if (!isAdmin.value || !ownerType) return
  try {
    if (ownerType === 'teacher') {
      const list = await teacherApi.options()
      ownerOptions.value = list.map((item) => ({
        id: item.id,
        label: `${item.name}（${item.department || '未设院系'}）`
      }))
      advisorOptions.value = list
    } else {
      const list = await studentApi.options()
      ownerOptions.value = list.map((item) => ({
        id: item.id,
        label: `${item.name}（${item.student_no}）`
      }))
      try {
        advisorOptions.value = await teacherApi.options()
      } catch (err) {
        advisorOptions.value = []
      }
    }
  } catch (err) {
    ownerOptions.value = []
  }
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, emptyForm())
  dialogVisible.value = true
  loadOwnerOptions(form.owner_type)
}

function openEdit(row) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    id: row.id,
    owner_type: row.owner_type,
    owner_id: row.owner_id,
    category: row.category,
    title: row.title,
    year: String(row.year),
    academic_year: row.academic_year || academicYearOf(row.year),
    level: row.level || '',
    role_rank: row.role_rank || '',
    advisor_id: row.advisor_id || null,
    indicator_ids: (row.indicators || []).map((item) => item.id),
    extra: { ...(row.extra || {}) },
    description: row.description || '',
    status: row.status || ''
  })
  dialogVisible.value = true
  loadOwnerOptions(row.owner_type)
  drawerVisible.value = false
}

function handleOwnerTypeChange(value) {
  form.owner_type = value
  form.owner_id = null
  form.category = ''
  form.level = ''
  form.extra = {}
  loadOwnerOptions(value)
}

function handleYearChange(value) {
  const year = Number(value)
  form.year = String(year)
  form.academic_year = academicYearOf(year)
}

function validate() {
  if (isAdmin.value && !form.owner_id) {
    toast.error('请选择所属人')
    return false
  }
  if (!form.category) {
    toast.error('请选择成果类型')
    return false
  }
  if (!form.title.trim()) {
    toast.error('请输入成果名称')
    return false
  }
  if (!form.year) {
    toast.error('请选择年份')
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validate()) return
  saving.value = true
  try {
    const payload = {
      category: form.category,
      title: form.title.trim(),
      year: Number(form.year),
      academic_year: form.academic_year,
      level: form.level,
      role_rank: form.role_rank,
      advisor_id: canPickAdvisor.value ? form.advisor_id : null,
      indicator_ids: form.indicator_ids,
      extra: form.extra,
      description: form.description
    }
    if (isAdmin.value) {
      payload.owner_type = form.owner_type
      payload.owner_id = form.owner_id
    }
    if (isElevated.value && form.status) payload.status = form.status
    if (dialogMode.value === 'create') {
      await achievementApi.create(payload)
      toast.success('成果新增成功')
    } else {
      await achievementApi.update(form.id, payload)
      toast.success('成果已更新')
    }
    dialogVisible.value = false
    await Promise.all([loadList(), loadMeta()])
  } catch (err) {
    // 统一错误处理
  } finally {
    saving.value = false
  }
}

function handleDelete(row) {
  askConfirm({
    title: '删除确认',
    description: `确认将成果「${row.title}」移入回收站吗？可在回收站恢复。`,
    confirmText: '移入回收站',
    danger: false,
    handler: async () => {
      await achievementApi.remove(row.id)
      toast.success('成果已移入回收站')
      if (items.value.length === 1 && page.value > 1) page.value -= 1
      loadList()
    }
  })
}

async function handleSubmitReview(row) {
  try {
    await achievementApi.submit(row.id)
    toast.success('已提交审核')
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

async function handleReview(row, action, comment) {
  try {
    await achievementApi.review(row.id, action, comment)
    toast.success(action === 'approve' ? '已通过' : '已驳回')
    loadList()
  } catch (err) {
    // 统一错误处理
  }
}

function handleReject(row) {
  openPrompt({
    title: '审核驳回',
    description: '请填写驳回意见，便于教师/学生修改后重新提交',
    value: '',
    textarea: true,
    placeholder: '驳回意见（必填）',
    confirmText: '确认驳回',
    validate: (value) => (value && value.trim() ? null : '驳回意见不能为空'),
    handler: (value) => handleReview(row, 'reject', value.trim())
  })
}

function openIndicators(row) {
  const selected = (row.indicators || []).map((item) => item.id)
  openPrompt({
    title: '关联认证指标点',
    description: '输入要关联的指标点编号，用逗号分隔，例如 1,5,12',
    value: selected.join(','),
    textarea: false,
    placeholder: '指标点编号，逗号分隔',
    confirmText: '确定关联',
    validate: (text) => {
      const ids = (text || '').split(/[,，\s]+/).filter(Boolean)
      if (!ids.length) return '请至少填写一个指标点编号'
      const valid = ids.every((id) => indicators.value.some((item) => String(item.id) === id))
      return valid ? null : '存在无效的指标点编号'
    },
    handler: async (value) => {
      const ids = value.split(/[,，\s]+/).filter(Boolean).map(Number)
      await achievementApi.update(row.id, { indicator_ids: ids })
      toast.success('指标点已更新')
      loadList()
    }
  })
}

function batchSetLevel() {
  const ids = selectedIds.value
  openPrompt({
    title: '批量设置级别',
    description: `将 ${ids.length} 条成果的级别统一设置为（只对支持该级别的成果生效）`,
    value: '',
    textarea: false,
    placeholder: '请输入级别',
    confirmText: '确定设置',
    validate: (value) => (value && value.trim() ? null : '请输入级别'),
    handler: async (value) => {
      const data = await achievementApi.batch('set_level', { ids, level: value.trim() })
      toast.success(`已更新 ${data.affected} 条，跳过 ${data.skipped} 条`)
      selectedIds.value = []
      loadList()
    }
  })
}

function batchAddIndicators() {
  const ids = selectedIds.value
  openPrompt({
    title: '批量关联指标点',
    description: '输入要追加关联的指标点编号，用逗号分隔，例如 1,5,12',
    value: '',
    textarea: false,
    placeholder: '指标点编号，逗号分隔',
    confirmText: '确定关联',
    validate: (value) => {
      const list = (value || '').split(/[,，\s]+/).filter(Boolean)
      if (!list.length) return '请至少填写一个指标点编号'
      return list.every((id) => indicators.value.some((item) => String(item.id) === id)) ? null : '存在无效的指标点编号'
    },
    handler: async (value) => {
      const list = value.split(/[,，\s]+/).filter(Boolean).map(Number)
      const data = await achievementApi.batch('add_indicators', { ids, indicator_ids: list })
      toast.success(`已处理 ${data.affected} 条`)
      selectedIds.value = []
      loadList()
    }
  })
}

function batchSetStatus() {
  const ids = selectedIds.value
  askConfirm({
    title: '批量审核',
    description: '确认将所选成果全部标记为「已通过」吗？',
    confirmText: '全部通过',
    danger: false,
    handler: async () => {
      const data = await achievementApi.batch('set_status', { ids, status: 'approved' })
      toast.success(`已处理 ${data.affected} 条`)
      selectedIds.value = []
      loadList()
    }
  })
}

function batchDelete() {
  const ids = selectedIds.value
  askConfirm({
    title: '批量删除',
    description: `确认将所选 ${ids.length} 条成果移入回收站吗？`,
    confirmText: '移入回收站',
    danger: true,
    handler: async () => {
      const data = await achievementApi.batch('delete', { ids })
      toast.success(`已处理 ${data.affected} 条`)
      selectedIds.value = []
      loadList()
    }
  })
}

function openDetail(row) {
  detail.value = row
  drawerVisible.value = true
}

function extraEntries(row) {
  if (!row || !row.extra_display) return []
  return Object.entries(row.extra_display).map(([label, value]) => ({ label, value }))
}

function openAttachments(row) {
  currentRow.value = row
  uploadCategory.value = '其他'
  attachmentVisible.value = true
  drawerVisible.value = false
  refreshRow(row.id)
}

async function refreshRow(id) {
  try {
    const data = await achievementApi.detail(id)
    currentRow.value = data
    const index = items.value.findIndex((item) => item.id === id)
    if (index >= 0) items.value[index] = data
    if (detail.value && detail.value.id === id) detail.value = data
  } catch (err) {
    // 统一错误处理
  }
}

async function onFilesSelected(event) {
  const files = Array.from(event.target.files || [])
  if (!currentRow.value || !files.length) return
  let uploaded = 0
  for (const file of files) {
    if (file.size > 20 * 1024 * 1024) {
      toast.warning('单个文件不能超过 20MB')
      continue
    }
    try {
      await achievementApi.uploadAttachments(currentRow.value.id, [file], uploadCategory.value)
      uploaded += 1
    } catch (err) {
      // 统一错误处理
    }
  }
  event.target.value = ''
  if (uploaded > 0) {
    toast.success('材料上传成功')
    await refreshRow(currentRow.value.id)
    loadList()
  }
}

function removeAttachment(row) {
  if (!currentRow.value) return
  askConfirm({
    title: '删除确认',
    description: `确认删除材料「${row.original_name}」吗？文件将被移除。`,
    confirmText: '删除',
    danger: true,
    handler: async () => {
      await achievementApi.removeAttachment(currentRow.value.id, row.id)
      toast.success('材料已删除')
      await refreshRow(currentRow.value.id)
      loadList()
    }
  })
}

async function downloadAttachment(row, preview) {
  const achievementId = currentRow.value ? currentRow.value.id : detail.value && detail.value.id
  if (!achievementId) return
  try {
    const response = await achievementApi.downloadAttachment(achievementId, row.id, preview)
    if (preview) {
      openBlob(response)
    } else {
      saveBlob(response, row.original_name)
    }
  } catch (err) {
    // 统一错误处理
  }
}

async function handleExport() {
  try {
    const response = await ioApi.exportAchievements(buildParams())
    saveBlob(response, '业绩成果清单.xlsx')
  } catch (err) {
    // 统一错误处理
  }
}

function askConfirm({ title, description, confirmText, danger, handler }) {
  confirmState.title = title
  confirmState.description = description
  confirmState.confirmText = confirmText
  confirmState.danger = danger
  confirmState.handler = handler
  confirmState.open = true
}

function onConfirm() {
  confirmState.open = false
  const handler = confirmState.handler
  confirmState.handler = null
  if (handler) handler()
}

function openPrompt({ title, description, value, textarea, placeholder, confirmText, validate, handler }) {
  promptState.title = title
  promptState.description = description || ''
  promptState.value = value || ''
  promptState.textarea = !!textarea
  promptState.placeholder = placeholder || ''
  promptState.confirmText = confirmText || '确认'
  promptState.validate = validate
  promptState.handler = handler
  promptState.open = true
}

async function confirmPrompt() {
  const error = promptState.validate ? promptState.validate(promptState.value) : null
  if (error) {
    toast.error(error)
    return
  }
  const handler = promptState.handler
  promptState.open = false
  promptState.handler = null
  if (handler) await handler(promptState.value)
}

onMounted(() => {
  applyQuery()
  loadMeta()
  loadList()
})
</script>