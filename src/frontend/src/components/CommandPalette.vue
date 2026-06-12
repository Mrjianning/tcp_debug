<template>
  <aside class="command-palette ubuntu-card">
    <div class="palette-header">
      <span>指令模板</span>
      <NTag size="small" round>src/json</NTag>
    </div>
    <section v-for="group in groups" :key="group.title" class="command-group">
      <div class="command-group-title">{{ group.title }}</div>
      <div class="command-buttons">
        <NButton
          v-for="item in group.items"
          :key="item.key"
          size="small"
          :type="activeKey === item.key ? 'primary' : 'default'"
          @click="$emit('load-json', item.key)"
        >
          {{ item.label }}
        </NButton>
      </div>
    </section>

    <section class="command-group">
      <div class="command-group-title">文件 / 模型</div>
      <div class="command-buttons">
        <NButton size="small" @click="$emit('open-mapping-file')">导入映射文件</NButton>
        <NButton size="small" @click="$emit('choose-mapping-export')">导出映射文件</NButton>
        <NButton size="small" @click="$emit('choose-dual-avg-export')">导出双能划线法</NButton>
        <NButton size="small" @click="$emit('open-model-file', 'detect')">新增检测模型</NButton>
        <NButton size="small" @click="$emit('open-model-file', 'segment')">新增分割模型</NButton>
        <NButton size="small" @click="$emit('open-model-file', 'rec')">新增识别模型</NButton>
      </div>
    </section>
  </aside>
</template>

<script setup>
import { NButton, NTag } from 'naive-ui';

defineProps({
  activeKey: { type: String, required: true },
  groups: { type: Array, required: true },
});

defineEmits([
  'choose-dual-avg-export',
  'choose-mapping-export',
  'load-json',
  'open-mapping-file',
  'open-model-file',
]);
</script>
