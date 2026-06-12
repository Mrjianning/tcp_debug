<template>
  <NModal :show="show" preset="card" title="喷阀模块管理" style="width: 72vw; max-width: 1100px" @update:show="$emit('update:show', $event)">
    <template v-if="workingJectorSystemParam">
      <NSpace justify="space-between" align="center" style="margin-bottom: 12px">
        <NSpace>
          <NTag>喷阀套数 {{ workingJectorSystemParam.jectorModules.length }}</NTag>
          <NTag>单元总数 {{ totalUnitCount }}</NTag>
        </NSpace>
        <NButton type="primary" @click="$emit('add-module')">新增模块</NButton>
      </NSpace>
      <NCard v-for="(module, moduleIndex) in workingJectorSystemParam.jectorModules" :key="moduleIndex" size="small" class="modal-section">
        <template #header>模块 {{ module.moduleId }}</template>
        <template #header-extra>
          <NSpace>
            <NButton size="small" @click="$emit('add-unit', moduleIndex)">新增单元</NButton>
            <NButton size="small" type="error" ghost @click="$emit('remove-module', moduleIndex)">删除模块</NButton>
          </NSpace>
        </template>
        <div class="module-grid">
          <label class="field-cell">
            <span>打击类型 <small>sprayWhat</small></span>
            <NInput :value="String(module.sprayWhat)" @update:value="$emit('update-module', moduleIndex, 'sprayWhat', $event)" />
          </label>
          <label class="field-cell">
            <span>喷阀布局 <small>ejectorLayout</small></span>
            <NInput :value="String(module.ejectorLayout)" @update:value="$emit('update-module', moduleIndex, 'ejectorLayout', $event)" />
          </label>
          <label class="field-cell">
            <span>合并信号 <small>isMergeSignal</small></span>
            <NInput :value="String(module.isMergeSignal)" @update:value="$emit('update-module', moduleIndex, 'isMergeSignal', $event)" />
          </label>
          <label class="field-cell">
            <span>电气延迟 <small>electricalDelayMs</small></span>
            <NInput :value="String(module.electricalDelayMs)" @update:value="$emit('update-module', moduleIndex, 'electricalDelayMs', $event)" />
          </label>
        </div>
        <div class="unit-table">
          <div class="unit-table-header">
            <span>单元ID</span>
            <span>控制器IP</span>
            <span>控制器端口</span>
            <span>喷嘴数量</span>
            <span>map文件</span>
            <span>操作</span>
          </div>
          <div v-for="(unit, unitIndex) in module.jectorUnits" :key="unitIndex" class="unit-row">
            <NTag>unit {{ unit.unitId }}</NTag>
            <NInput :value="unit.controllerIp" @update:value="$emit('update-unit', moduleIndex, unitIndex, 'controllerIp', $event)" />
            <NInput :value="String(unit.controllerPort)" @update:value="$emit('update-unit', moduleIndex, unitIndex, 'controllerPort', $event)" />
            <NInput :value="String(unit.nozzleCount)" @update:value="$emit('update-unit', moduleIndex, unitIndex, 'nozzleCount', $event)" />
            <span class="map-file-list">{{ (unit.mapfiles || []).map(item => item.name || item.fileName).filter(Boolean).join(', ') || '无 map 文件' }}</span>
            <NButton size="small" type="error" ghost @click="$emit('remove-unit', moduleIndex, unitIndex)">删除</NButton>
          </div>
        </div>
      </NCard>
    </template>
    <NEmpty v-else description="暂无喷阀模块数据" />
    <template #footer>
      <NSpace justify="end">
        <NButton @click="$emit('update:show', false)">取消</NButton>
        <NButton type="primary" @click="$emit('confirm')">确认应用</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<script setup>
import { computed } from 'vue';
import { NButton, NCard, NEmpty, NInput, NModal, NSpace, NTag } from 'naive-ui';

const props = defineProps({
  show: { type: Boolean, required: true },
  workingJectorSystemParam: { type: Object, default: null },
});

defineEmits([
  'add-module',
  'add-unit',
  'confirm',
  'remove-module',
  'remove-unit',
  'update-module',
  'update-unit',
  'update:show',
]);

const totalUnitCount = computed(() =>
  props.workingJectorSystemParam
    ? props.workingJectorSystemParam.jectorModules.reduce((sum, module) => sum + module.jectorUnits.length, 0)
    : 0,
);
</script>
