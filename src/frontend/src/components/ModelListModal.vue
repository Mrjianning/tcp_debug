<template>
  <NModal :show="show" preset="card" title="模型列表" style="width: 64vw; max-width: 980px" @update:show="$emit('update:show', $event)">
    <template v-if="latestModelListSummary">
      <NCard v-for="group in latestModelListSummary.groups" :key="group.key" size="small" class="modal-section">
        <template #header>{{ group.title }}</template>
        <NDataTable :columns="modelColumns(group.key)" :data="group.items" :pagination="false" size="small" />
      </NCard>
    </template>
    <NEmpty v-else description="暂无模型列表数据" />
  </NModal>
</template>

<script setup>
import { h } from 'vue';
import { NButton, NCard, NDataTable, NEmpty, NModal } from 'naive-ui';

defineProps({
  latestModelListSummary: { type: Object, default: null },
  show: { type: Boolean, required: true },
});

const emit = defineEmits(['prepare-delete', 'update:show']);

function modelColumns(groupKey) {
  return [
    { title: 'modelId', key: 'modelId', width: 120 },
    { title: 'modelName', key: 'modelName' },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      render(row) {
        return h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => emit('prepare-delete', groupKey, row) }, { default: () => '删除' });
      },
    },
  ];
}
</script>
