<template>
  <div class="flex flex-wrap items-center justify-end gap-3">
    <span class="text-sm text-muted-foreground">共 {{ total }} 条</span>

    <Select
      :model-value="String(pageSize)"
      @update:model-value="onSizeChange(Number($event))"
    >
      <SelectTrigger class="h-8 w-[88px] text-xs">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem v-for="s in pageSizes" :key="s" :value="String(s)">
          {{ s }} / 页
        </SelectItem>
      </SelectContent>
    </Select>

    <div class="flex items-center gap-1">
      <Button variant="outline" size="sm" :disabled="page <= 1" @click="emit({ page: page - 1, pageSize })">
        上一页
      </Button>
      <span class="min-w-[96px] text-center text-sm text-muted-foreground">
        {{ page }} / {{ totalPages }}
      </span>
      <Button
        variant="outline"
        size="sm"
        :disabled="page >= totalPages"
        @click="emit({ page: page + 1, pageSize })"
      >
        下一页
      </Button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 },
  pageSizes: { type: Array, default: () => [10, 20, 50] }
})

const emit = defineEmits(['change'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

function onSizeChange(size) {
  emit({ page: 1, pageSize: size })
}
</script>