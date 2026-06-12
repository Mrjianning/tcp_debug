<template>
  <section class="terminal-panel ubuntu-card">
    <div class="terminal-titlebar">
      <div class="terminal-dots" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <div>
        <div class="panel-title">日志输出</div>
        <div class="panel-subtitle">自动滚动 / 事件过滤 / 终端配色</div>
      </div>
    </div>
    <div ref="logBoxRef" class="terminal-window">
      <span v-for="(line, index) in logs" :key="index" :class="['log-line', `log-${line.type}`]">
        {{ line.text }}
      </span>
    </div>
  </section>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue';

const props = defineProps({
  logs: { type: Array, required: true },
});

const logBoxRef = ref(null);

watch(
  () => props.logs.length,
  () => {
    nextTick(() => {
      if (logBoxRef.value) {
        logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight;
      }
    });
  },
);
</script>
