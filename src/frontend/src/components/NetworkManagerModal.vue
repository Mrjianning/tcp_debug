<template>
  <NModal :show="show" preset="card" title="网络管理" style="width: 78vw; max-width: 1180px" @update:show="$emit('update:show', $event)">
    <div class="network-manager">
      <div class="network-toolbar">
        <NSpace align="center">
          <NTag :type="interfaces.length ? 'success' : 'warning'">网口数量 {{ interfaces.length }}</NTag>
          <NTag type="info">netplan + NetworkManager</NTag>
        </NSpace>
        <NSpace>
          <NButton size="small" :loading="loading" @click="$emit('refresh')">刷新网口</NButton>
          <NButton size="small" type="primary" ghost @click="$emit('preview')">生成预览</NButton>
        </NSpace>
      </div>

      <NAlert type="warning" :show-icon="false" class="network-alert">
        为避免失联，当前浏览器连接正在使用的网口不能在网页中直接修改名称或 IP；请改用本机桌面、串口或另一块网口操作。
      </NAlert>
      <NAlert v-if="error" type="error" :show-icon="false" class="network-alert">{{ error }}</NAlert>

        <div class="network-table">
        <div class="network-table-header">
          <span>配置</span>
          <span>网口名称</span>
          <span>IPv4地址</span>
          <span>MAC地址</span>
          <span>网线状态</span>
          <span>当前Web连接</span>
          <span>目标名称</span>
          <span>静态IP</span>
        </div>
        <div v-for="(item, index) in interfaces" :key="item.macAddress || item.name" class="network-row">
          <NCheckbox
            :checked="item.configureEnabled"
            :disabled="item.isActiveWebInterface"
            @update:checked="$emit('update-interface', index, 'configureEnabled', $event)"
          />
          <span class="network-name">{{ item.name }}</span>
          <span class="network-ip">{{ item.ipv4Address || '未配置' }}</span>
          <span class="network-mac">{{ item.macAddress || '未知' }}</span>
          <NTag size="small" :type="item.linkDetected ? 'success' : 'default'">
            {{ item.linkDetected ? '已插入网线' : '未插入网线' }}
          </NTag>
          <NTag v-if="item.isActiveWebInterface" size="small" type="warning">当前Web连接</NTag>
          <span v-else class="network-muted">-</span>
          <NInput
            :value="item.targetName"
            :disabled="!item.configureEnabled || item.isActiveWebInterface"
            placeholder="目标名称"
            @update:value="$emit('update-interface', index, 'targetName', $event)"
          />
          <NInput
            :value="item.ipv4Address"
            :disabled="!item.configureEnabled || item.isActiveWebInterface"
            placeholder="10.66.71.101 或 10.66.71.101/24"
            @update:value="$emit('update-interface', index, 'ipv4Address', $event)"
          />
        </div>
      </div>

      <div class="network-preview">
        <div class="panel-titlebar">
          <div>
            <div class="panel-title">配置预览</div>
            <div class="panel-subtitle">应用前请确认 MAC、目标名称、静态IP 对应关系；未写掩码时默认 /24</div>
          </div>
          <NButton type="warning" :loading="applying" @click="$emit('apply')">应用配置</NButton>
        </div>
        <pre>{{ yamlPreview || '点击「生成预览」查看将写入的 netplan 配置' }}</pre>
      </div>
    </div>
  </NModal>
</template>

<script setup>
import { NAlert, NButton, NCheckbox, NInput, NModal, NSpace, NTag } from 'naive-ui';

defineProps({
  applying: { type: Boolean, default: false },
  error: { type: String, default: '' },
  interfaces: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  show: { type: Boolean, required: true },
  yamlPreview: { type: String, default: '' },
});

defineEmits([
  'apply',
  'preview',
  'refresh',
  'update-interface',
  'update:show',
]);
</script>
