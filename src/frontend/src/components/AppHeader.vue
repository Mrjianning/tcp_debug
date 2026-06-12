<template>
  <header class="ubuntu-topbar">
    <div class="app-identity">
      <div class="window-dots" aria-hidden="true">
        <span class="dot close"></span>
        <span class="dot minimize"></span>
        <span class="dot maximize"></span>
      </div>
      <div>
        <div class="brand-title">选矿服务 TCP 调试台</div>
        <div class="brand-subtitle"> </div>
      </div>
    </div>

    <div class="connection-summary">
      <span :class="['connection-pill', isConnected ? 'online' : 'offline']">
        {{ isConnected ? 'TCP 已连接' : 'TCP 未连接' }}
      </span>
      <span class="summary-item">WS 8765</span>
      <span class="summary-item">目标 {{ ip }}:{{ port }}</span>
      <span class="summary-item">日志 {{ logCount }}</span>
      <span class="summary-item">模板 {{ activeTemplateLabel }}</span>
    </div>

    <div class="connection-form">
      <NInput :value="ip" placeholder="服务器IP" style="width: 150px" @update:value="$emit('update:ip', $event)" />
      <NInput :value="port" placeholder="端口" style="width: 88px" @update:value="$emit('update:port', $event)" />
      <NButton type="primary" :loading="connecting" :disabled="isConnected" @click="$emit('connect')">
        {{ isConnected ? '已连接' : '连接' }}
      </NButton>
      <NButton type="error" ghost :disabled="!isConnected" @click="$emit('disconnect')">断开</NButton>
    </div>
  </header>
</template>

<script setup>
import { NButton, NInput } from 'naive-ui';

defineProps({
  activeTemplateLabel: { type: String, required: true },
  connecting: { type: Boolean, required: true },
  ip: { type: String, required: true },
  isConnected: { type: Boolean, required: true },
  logCount: { type: Number, required: true },
  port: { type: String, required: true },
});

defineEmits(['connect', 'disconnect', 'update:ip', 'update:port']);
</script>
