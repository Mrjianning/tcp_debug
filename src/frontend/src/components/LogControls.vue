<template>
  <section class="log-controls ubuntu-card">
    <div class="control-block">
      <div class="control-title">显示事件</div>
      <div class="checkbox-row">
        <NCheckbox
          v-for="event in eventTypeOptions"
          :key="event.value"
          :checked="!hiddenEventTypes.has(event.value)"
          @update:checked="$emit('set-event-visible', event.value, $event)"
        >
          {{ event.label }}
        </NCheckbox>
      </div>
    </div>

    <div class="control-block">
      <div class="control-title">格式化日志</div>
      <div class="checkbox-row">
        <NCheckbox
          v-for="event in eventTypeOptions"
          :key="event.value"
          :checked="formattedEventTypes.has(event.value)"
          @update:checked="$emit('set-event-formatted', event.value, $event)"
        >
          {{ event.label }}
        </NCheckbox>
      </div>
    </div>

    <div class="control-actions">
      <NButton size="small" @click="$emit('clear-logs')">清空日志</NButton>
      <NButton size="small" @click="$emit('show-network-manager')">网络管理</NButton>
      <NButton size="small" @click="$emit('show-jector-modules')">喷阀模块管理</NButton>
      <NButton size="small" @click="$emit('show-model-list')">查看模型列表</NButton>
      <NButton size="small" @click="$emit('show-event-defs')">查看事件定义</NButton>
    </div>
  </section>
</template>

<script setup>
import { NButton, NCheckbox } from 'naive-ui';

defineProps({
  eventTypeOptions: { type: Array, required: true },
  formattedEventTypes: { type: Set, required: true },
  hiddenEventTypes: { type: Set, required: true },
});

defineEmits([
  'clear-logs',
  'set-event-formatted',
  'set-event-visible',
  'show-event-defs',
  'show-jector-modules',
  'show-model-list',
  'show-network-manager',
]);
</script>
