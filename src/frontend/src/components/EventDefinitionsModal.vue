<template>
  <NModal :show="show" preset="card" title="事件定义" style="width: 72vw; max-width: 1100px" @update:show="$emit('update:show', $event)">
    <NGrid :cols="2" :x-gap="12" :y-gap="12">
      <NGi v-for="group in eventDefinitions" :key="group.name">
        <NCard size="small">
          <template #header>{{ group.title }}</template>
          <template #header-extra><NTag size="small">{{ group.name }}</NTag></template>
          <NDataTable :columns="eventDefColumns" :data="group.items" :pagination="false" size="small" max-height="260" />
        </NCard>
      </NGi>
    </NGrid>
  </NModal>
</template>

<script setup>
import { NCard, NDataTable, NGi, NGrid, NModal, NTag } from 'naive-ui';

defineProps({
  eventDefinitions: { type: Array, required: true },
  show: { type: Boolean, required: true },
});

defineEmits(['update:show']);

const eventDefColumns = [
  { title: '名称', key: 'name' },
  { title: '值', key: 'value', width: 70 },
  { title: '说明', key: 'description' },
];
</script>
