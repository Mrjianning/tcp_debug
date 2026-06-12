<template>
  <section class="json-panel ubuntu-card">
    <div class="panel-titlebar">
      <div>
        <div class="panel-title">自定义 JSON</div>
        <div class="panel-subtitle">编辑并发送单行 JSON 指令</div>
      </div>
      <NButton type="warning" @click="$emit('send')">发送 JSON</NButton>
    </div>
    <NInput
      :value="value"
      class="json-editor"
      type="textarea"
      :autosize="{ minRows: 20 }"
      spellcheck="false"
      @update:value="$emit('update:value', $event)"
    />
  </section>
</template>

<script setup>
import { NButton, NInput } from 'naive-ui';

defineProps({
  value: { type: String, required: true },
});

defineEmits(['send', 'update:value']);
</script>
