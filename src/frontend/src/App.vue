<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <div class="ubuntu-shell">
        <AppHeader
          v-model:ip="ip"
          v-model:port="port"
          :active-template-label="activeTemplateLabel"
          :connecting="connecting"
          :is-connected="isConnected"
          :log-count="logs.length"
          @connect="connectServer"
          @disconnect="disconnectServer"
        />

        <main class="ubuntu-workspace">
          <CommandPalette
            :active-key="activeKey"
            :groups="commandGroups"
            @choose-dual-avg-export="chooseDualAvgExportPath"
            @choose-mapping-export="chooseMappingExportPath"
            @load-json="loadJson"
            @open-mapping-file="openMappingFilePicker"
            @open-model-file="openModelFilePicker"
          />

          <section class="workspace-main">
            <LogControls
              :event-type-options="eventTypeOptions"
              :formatted-event-types="formattedEventTypes"
              :hidden-event-types="hiddenEventTypes"
              @clear-logs="clearLogs"
              @set-event-formatted="setEventFormatted"
              @set-event-visible="setEventVisible"
              @show-event-defs="showEventDefs"
              @show-jector-modules="showJectorModules"
              @show-model-list="showModelList"
              @show-network-manager="showNetworkManager"
            />

            <div class="editor-log-grid">
              <JsonEditorPanel v-model:value="jsonText" @send="sendCustomJson" />
              <TerminalLogPanel :logs="logs" />
            </div>
          </section>
        </main>

        <input ref="mappingFileInput" type="file" hidden @change="handleMappingFileSelected">
        <input ref="detectModelFileInput" type="file" hidden @change="handleModelFileSelected('detect', $event)">
        <input ref="segmentModelFileInput" type="file" hidden @change="handleModelFileSelected('segment', $event)">
        <input ref="recModelFileInput" type="file" hidden @change="handleModelFileSelected('rec', $event)">

        <JectorModal
          v-model:show="jectorModalVisible"
          :working-jector-system-param="workingJectorSystemParam"
          @add-module="addJectorModule"
          @add-unit="addJectorUnit"
          @confirm="confirmJectorModules"
          @remove-module="removeJectorModule"
          @remove-unit="removeJectorUnit"
          @update-module="updateJectorModule"
          @update-unit="updateJectorUnit"
        />
        <ModelListModal
          v-model:show="modelListVisible"
          :latest-model-list-summary="latestModelListSummary"
          @prepare-delete="prepareDeleteModelCommand"
        />
        <EventDefinitionsModal
          v-model:show="eventDefsVisible"
          :event-definitions="eventDefinitions"
        />
        <NetworkManagerModal
          v-model:show="networkModalVisible"
          :applying="networkApplying"
          :error="networkError"
          :interfaces="networkInterfaces"
          :loading="networkLoading"
          :yaml-preview="networkYamlPreview"
          @apply="applyNetworkConfig"
          @preview="previewNetworkConfig"
          @refresh="refreshNetworkInterfaces"
          @update-interface="updateNetworkInterface"
        />
        </div>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup>
import { computed, ref } from 'vue';
import { NConfigProvider, NDialogProvider, NMessageProvider, createDiscreteApi } from 'naive-ui';
import AppHeader from './components/AppHeader.vue';
import CommandPalette from './components/CommandPalette.vue';
import EventDefinitionsModal from './components/EventDefinitionsModal.vue';
import JectorModal from './components/JectorModal.vue';
import JsonEditorPanel from './components/JsonEditorPanel.vue';
import LogControls from './components/LogControls.vue';
import ModelListModal from './components/ModelListModal.vue';
import NetworkManagerModal from './components/NetworkManagerModal.vue';
import TerminalLogPanel from './components/TerminalLogPanel.vue';
import {
  EVENT_TYPE_NAMES,
  addJectorModuleToParam,
  addJectorUnitToModule,
  applyDetectModelFileData,
  applyMappingFileData,
  applyMappingOutputPath,
  applyRecModelFileData,
  applySegmentModelFileData,
  buildDeleteModelCommand,
  buildSetParamsFromReceivedData,
  extractJectorSystemSummary,
  extractModelListSummary,
  formatReceivedLogMessage,
  isSuccessfulParamReadResponse,
  normalizeJectorSystemParam,
  removeJectorModuleFromParam,
  removeJectorUnitFromModule,
  shouldDisplayMessage,
  updateJectorModuleField,
  updateJectorUnitField,
} from './lib/protocol.mjs';

const commandJsonFiles = {
  start: 'json/startSorting.json',
  stop: 'json/stopSorting.json',
  empty: 'json/updateEmpty.json',
  air: 'json/updateAir.json',
  get: 'json/getParams.json',
  modelList: 'json/getModelList.json',
  set: 'json/setParams.json',
  productSubType: 'json/setProductSubType.json',
  realtimeUpdate: 'json/realtimeUpdateParams.json',
  ejectorSelfCheck: 'json/ejectorSelfCheck.json',
  ejectorLoopCheck: 'json/ejectorLoopCheck.json',
  deleteDetectModel: 'json/deleteDetectModelTemplate.json',
  deleteSegmentModel: 'json/deleteSegmentModelTemplate.json',
  deleteRecModel: 'json/deleteRecModelTemplate.json',
};

const mappingImportTemplateFile = 'json/mappingImportTemplate.json';
const mappingExportTemplateFile = 'json/mappingExportTemplate.json';
const dualAvgExportTemplateFile = 'json/dualAvgExportTemplate.json';
const addDetectModelTemplateFile = 'json/addDetectModelTemplate.json';
const addSegmentModelTemplateFile = 'json/addSegmentModelTemplate.json';
const addRecModelTemplateFile = 'json/addRecModelTemplate.json';
const eventDefinitionsFile = 'json/eventDefinitions.json';

const commandGroups = [
  {
    title: '选矿指令',
    items: [
      { key: 'start', label: '开启选矿' },
      { key: 'stop', label: '关闭选矿' },
      { key: 'empty', label: '更新本底' },
      { key: 'air', label: '更新空场' },
    ],
  },
  {
    title: '配置参数',
    items: [
      { key: 'get', label: '参数获取' },
      { key: 'set', label: '参数写入' },
      { key: 'productSubType', label: '设置产品子类型' },
      { key: 'realtimeUpdate', label: '实时更新参数' },
    ],
  },
  {
    title: '喷阀 / 模型',
    items: [
      { key: 'ejectorSelfCheck', label: '喷阀自检' },
      { key: 'ejectorLoopCheck', label: '喷阀循环检测' },
      { key: 'modelList', label: '获取模型列表' },
      { key: 'deleteDetectModel', label: '删除检测模型' },
      { key: 'deleteSegmentModel', label: '删除分割模型' },
      { key: 'deleteRecModel', label: '删除识别模型' },
    ],
  },
];

const actionLabelMap = Object.fromEntries(
  commandGroups.flatMap((group) => group.items).map((item) => [item.key, item.label]),
);

const themeOverrides = {
  common: {
    borderRadius: '8px',
    primaryColor: '#e95420',
    primaryColorHover: '#f26b38',
    primaryColorPressed: '#c34113',
    warningColor: '#e95420',
    warningColorHover: '#f26b38',
  },
};

const ip = ref('10.66.71.240');
const port = ref('9000');
const ws = ref(null);
const isConnected = ref(false);
const connecting = ref(false);
const jsonText = ref('');
const activeKey = ref('');
const logs = ref([]);
const hiddenEventTypes = ref(new Set());
const formattedEventTypes = ref(new Set());
const latestParamReadData = ref(null);
const latestJectorSystemSummary = ref(null);
const latestModelListSummary = ref(null);
const workingJectorSystemParam = ref(null);
const jectorModalVisible = ref(false);
const modelListVisible = ref(false);
const eventDefsVisible = ref(false);
const eventDefinitions = ref([]);
const networkModalVisible = ref(false);
const networkInterfaces = ref([]);
const networkYamlPreview = ref('');
const networkLoading = ref(false);
const networkApplying = ref(false);
const networkError = ref('');
const mappingFileInput = ref(null);
const detectModelFileInput = ref(null);
const segmentModelFileInput = ref(null);
const recModelFileInput = ref(null);
const { message, dialog } = createDiscreteApi(['message', 'dialog']);

const eventTypeOptions = computed(() =>
  Object.entries(EVENT_TYPE_NAMES).map(([value, label]) => ({ value: Number(value), label })),
);
const activeTemplateLabel = computed(() => actionLabelMap[activeKey.value] || '未选择');

function nowTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false });
}

function log(text, type = 'system') {
  logs.value.push({ text: type === 'system' ? `[${nowTime()}] ${text}` : text, type });
  while (logs.value.length > 2000) logs.value.shift();
}

function clearLogs() {
  logs.value = [];
}

function setEventVisible(eventType, visible) {
  const next = new Set(hiddenEventTypes.value);
  if (visible) next.delete(eventType);
  else next.add(eventType);
  hiddenEventTypes.value = next;
}

function setEventFormatted(eventType, formatted) {
  const next = new Set(formattedEventTypes.value);
  if (formatted) next.add(eventType);
  else next.delete(eventType);
  formattedEventTypes.value = next;
}

function getWsUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.hostname}:8765`;
}

function connectServer() {
  if (isConnected.value) {
    log('已连接，请勿重复操作');
    return;
  }
  const portNumber = Number(port.value);
  if (!ip.value.trim()) {
    log('服务器IP不能为空');
    return;
  }
  if (!Number.isInteger(portNumber) || portNumber < 1 || portNumber > 65535) {
    log('端口必须是 1-65535');
    return;
  }
  connecting.value = true;
  ws.value = new WebSocket(getWsUrl());
  ws.value.onopen = () => {
    ws.value.send(JSON.stringify({ action: 'connect', ip: ip.value.trim(), port: portNumber }));
  };
  ws.value.onmessage = (event) => handleMessage(JSON.parse(event.data));
  ws.value.onclose = () => {
    isConnected.value = false;
    connecting.value = false;
    log('WebSocket 连接已关闭');
  };
  ws.value.onerror = () => {
    isConnected.value = false;
    connecting.value = false;
    log('WebSocket 错误');
  };
}

function disconnectServer() {
  if (!isConnected.value || !ws.value) {
    log('未连接服务器');
    return;
  }
  ws.value.send(JSON.stringify({ action: 'disconnect' }));
}

function sendCustomJson() {
  if (!isConnected.value || !ws.value) {
    log('请先连接服务器');
    return;
  }
  ws.value.send(JSON.stringify({ action: 'send', data: jsonText.value.trim() }));
}

async function loadJson(key) {
  activeKey.value = key;
  const file = commandJsonFiles[key];
  if (!file) {
    log('未找到对应指令JSON文件');
    return;
  }
  try {
    const response = await fetch(file, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    jsonText.value = JSON.stringify(data, null, 2);
    log(`已加载 ${file}，可手动修改编辑`);
  } catch (err) {
    log(`加载指令JSON失败: ${file} ${err.message}`);
  }
}

async function fetchJson(file) {
  const response = await fetch(file, { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function handleMessage(msg) {
  if (!shouldDisplayMessage(msg, hiddenEventTypes.value)) return;
  if (msg._type === 'system') {
    log(msg.msg);
    if (msg.msg.includes('连接成功')) {
      isConnected.value = true;
      connecting.value = false;
    } else if (msg.msg.includes('断开连接') || msg.msg.includes('连接失败') || msg.msg.includes('已请求断开连接')) {
      isConnected.value = false;
      connecting.value = false;
    }
    return;
  }
  if (msg._type === 'json') {
    log(formatReceivedLogMessage(msg.data, formattedEventTypes.value), msg.tag || 'raw');
    const receivedData = msg.data && msg.data.params && msg.data.params.data;
    if (receivedData && typeof receivedData === 'object') {
      const jectorSummary = extractJectorSystemSummary(receivedData);
      if (jectorSummary) latestJectorSystemSummary.value = jectorSummary;
      const params = msg.data && msg.data.params;
      if (params && params.operationCommand === 5 && params.operationResult === 2 && params.paramType === 20) {
        latestModelListSummary.value = extractModelListSummary(receivedData);
      }
    }
    fillSetParamsFromParamReadResponse(msg.data);
    return;
  }
  if (msg._type === 'raw') {
    log(`[${nowTime()}] 接收原始数据: ${msg.raw}`, 'raw');
  }
}

async function fillSetParamsFromParamReadResponse(data) {
  if (!isSuccessfulParamReadResponse(data)) return;
  latestParamReadData.value = data.params.data;
  const template = await fetchJson(commandJsonFiles.set);
  jsonText.value = JSON.stringify(buildSetParamsFromReceivedData(template, latestParamReadData.value), null, 2);
  activeKey.value = 'set';
  log('已根据参数读取响应填充参数写入 JSON');
  try {
    await saveSetParamsTemplate(latestParamReadData.value);
    log('已保存实际参数到 setParams.json');
  } catch (err) {
    log(`保存实际参数到 setParams.json 失败: ${err.message}`);
  }
}

function openMappingFilePicker() {
  mappingFileInput.value?.click();
}

function openModelFilePicker(type) {
  const refs = {
    detect: detectModelFileInput,
    segment: segmentModelFileInput,
    rec: recModelFileInput,
  };
  refs[type]?.value?.click();
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      const commaIndex = result.indexOf(',');
      resolve(commaIndex >= 0 ? result.slice(commaIndex + 1) : result);
    };
    reader.onerror = () => reject(reader.error || new Error('读取文件失败'));
    reader.readAsDataURL(file);
  });
}

async function handleMappingFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    const template = await fetchJson(mappingImportTemplateFile);
    jsonText.value = JSON.stringify(applyMappingFileData(template, {
      name: file.name,
      size: file.size,
      base64Data: await readFileAsBase64(file),
    }), null, 2);
    log(`已导入映射文件 ${file.name}，大小 ${file.size} 字节`);
  } catch (err) {
    log(`导入映射文件失败: ${err.message}`);
  } finally {
    event.target.value = '';
  }
}

async function chooseMappingExportPath() {
  await chooseOutputPath(mappingExportTemplateFile, '选择映射文件导出目录', '已设置映射导出路径');
}

async function chooseDualAvgExportPath() {
  await chooseOutputPath(dualAvgExportTemplateFile, '选择双能划线法配置导出目录', '已设置双能划线法配置导出路径');
}

async function chooseDirectoryPath(title) {
  const response = await fetch(`/api/choose-directory?title=${encodeURIComponent(title)}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  return String(data.path || '').trim();
}

async function chooseOutputPath(templateFile, pickerTitle, successText) {
  try {
    const template = await fetchJson(templateFile);
    const outputPath = await chooseDirectoryPath(pickerTitle);
    if (!outputPath) return;
    jsonText.value = JSON.stringify(applyMappingOutputPath(template, outputPath), null, 2);
    log(`${successText}: ${outputPath}`);
  } catch (err) {
    log(`设置导出路径失败: ${err.message}`);
  }
}

async function handleModelFileSelected(type, event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  const config = {
    detect: [addDetectModelTemplateFile, applyDetectModelFileData, '检测模型'],
    segment: [addSegmentModelTemplateFile, applySegmentModelFileData, '分割模型'],
    rec: [addRecModelTemplateFile, applyRecModelFileData, '识别模型'],
  }[type];
  try {
    const template = await fetchJson(config[0]);
    jsonText.value = JSON.stringify(config[1](template, {
      name: file.name,
      size: file.size,
      base64Data: await readFileAsBase64(file),
    }), null, 2);
    log(`已导入${config[2]} ${file.name}，大小 ${file.size} 字节`);
  } catch (err) {
    log(`导入模型失败: ${err.message}`);
  } finally {
    event.target.value = '';
  }
}

function showJectorModules() {
  if (latestJectorSystemSummary.value) {
    workingJectorSystemParam.value = normalizeJectorSystemParam(latestJectorSystemSummary.value.raw);
  }
  jectorModalVisible.value = true;
}

function addJectorModule() {
  workingJectorSystemParam.value = addJectorModuleToParam(workingJectorSystemParam.value);
}

function removeJectorModule(moduleIndex) {
  workingJectorSystemParam.value = removeJectorModuleFromParam(workingJectorSystemParam.value, moduleIndex);
}

function addJectorUnit(moduleIndex) {
  workingJectorSystemParam.value = addJectorUnitToModule(workingJectorSystemParam.value, moduleIndex);
}

function removeJectorUnit(moduleIndex, unitIndex) {
  workingJectorSystemParam.value = removeJectorUnitFromModule(workingJectorSystemParam.value, moduleIndex, unitIndex);
}

function updateJectorModule(moduleIndex, field, value) {
  workingJectorSystemParam.value = updateJectorModuleField(workingJectorSystemParam.value, moduleIndex, field, value);
}

function updateJectorUnit(moduleIndex, unitIndex, field, value) {
  workingJectorSystemParam.value = updateJectorUnitField(workingJectorSystemParam.value, moduleIndex, unitIndex, field, value);
}

async function confirmJectorModules() {
  if (!workingJectorSystemParam.value || !latestParamReadData.value) {
    log('暂无可应用的参数读取数据');
    return;
  }
  const template = await fetchJson(commandJsonFiles.set);
  jsonText.value = JSON.stringify(buildSetParamsFromReceivedData(template, latestParamReadData.value, workingJectorSystemParam.value), null, 2);
  jectorModalVisible.value = false;
  activeKey.value = 'set';
  log('已应用喷阀模块修改到参数写入 JSON');
}

function showModelList() {
  modelListVisible.value = true;
}

async function fetchNetworkJson(url, options = {}) {
  const response = await fetch(url, {
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

async function saveSetParamsTemplate(receivedData) {
  return fetchNetworkJson('/api/json/update-set-params', {
    method: 'POST',
    body: JSON.stringify({ data: receivedData }),
  });
}

async function showNetworkManager() {
  networkModalVisible.value = true;
  await refreshNetworkInterfaces();
}

async function refreshNetworkInterfaces() {
  networkLoading.value = true;
  networkError.value = '';
  try {
    const data = await fetchNetworkJson('/api/network/interfaces');
    networkInterfaces.value = (data.interfaces || []).map((item) => ({
      ...item,
      configureEnabled: Boolean(item.configureEnabled ?? (item.linkDetected && item.ipv4Address)),
      targetName: item.targetName || item.name,
      ipv4Address: item.ipv4Address || '',
    }));
    networkYamlPreview.value = '';
    log(`已读取网口信息，共 ${networkInterfaces.value.length} 个网口`);
    message.success(`已读取 ${networkInterfaces.value.length} 个网口`);
  } catch (err) {
    networkError.value = err.message;
    log(`读取网口信息失败: ${err.message}`);
    message.error(`读取网口信息失败: ${err.message}`);
  } finally {
    networkLoading.value = false;
  }
}

function updateNetworkInterface(index, field, value) {
  networkInterfaces.value = networkInterfaces.value.map((item, itemIndex) =>
    itemIndex === index ? { ...item, [field]: value } : item,
  );
}

function getEnabledNetworkInterfaces() {
  return networkInterfaces.value.filter((item) => item.configureEnabled);
}

async function previewNetworkConfig() {
  networkError.value = '';
  try {
    const data = await fetchNetworkJson('/api/network/preview', {
      method: 'POST',
      body: JSON.stringify({ interfaces: getEnabledNetworkInterfaces() }),
    });
    networkYamlPreview.value = data.yaml || '';
    log('已生成网络配置预览');
    message.success('网络配置预览已生成');
  } catch (err) {
    networkError.value = err.message;
    log(`生成网络配置预览失败: ${err.message}`);
    message.error(`生成网络配置预览失败: ${err.message}`);
  }
}

async function applyNetworkConfig() {
  networkApplying.value = true;
  networkError.value = '';
  const applyingMessage = message.loading('正在应用网络配置...', { duration: 0 });
  try {
    const data = await fetchNetworkJson('/api/network/apply', {
      method: 'POST',
      body: JSON.stringify({ interfaces: getEnabledNetworkInterfaces() }),
    });
    networkYamlPreview.value = data.yaml || networkYamlPreview.value;
    if (Array.isArray(data.repairedFiles) && data.repairedFiles.length) {
      log(`已备份无效 netplan 配置: ${data.repairedFiles.join(', ')}`);
    }
    if (!data.ok) {
      const detail = data.error || '请查看 netplan/systemctl 输出';
      networkError.value = detail;
      log(`网络配置应用失败: ${detail}`);
      message.error('网络配置应用失败');
      dialog.error({
        title: '网络配置应用失败',
        content: detail,
        positiveText: '知道了',
      });
      return;
    }
    log('网络配置已应用');
    message.success('网络配置已应用');
    dialog.success({
      title: '网络配置已应用',
      content: 'netplan 配置已写入并应用完成。若修改了非当前连接网口，可以刷新网口信息确认最新状态。',
      positiveText: '刷新网口',
      onPositiveClick: () => {
        refreshNetworkInterfaces();
      },
    });
    await refreshNetworkInterfaces();
  } catch (err) {
    networkError.value = err.message;
    log(`网络配置应用失败: ${err.message}`);
    message.error('网络配置应用失败');
    dialog.error({
      title: '网络配置应用失败',
      content: err.message,
      positiveText: '知道了',
    });
  } finally {
    applyingMessage.destroy();
    networkApplying.value = false;
  }
}

async function prepareDeleteModelCommand(groupKey, model) {
  const templateFile = {
    detect: commandJsonFiles.deleteDetectModel,
    segment: commandJsonFiles.deleteSegmentModel,
    rec: commandJsonFiles.deleteRecModel,
  }[groupKey];
  const template = await fetchJson(templateFile);
  jsonText.value = JSON.stringify(buildDeleteModelCommand(template, model), null, 2);
  modelListVisible.value = false;
  log(`已生成删除模型命令: modelType=${model.modelType}, modelId=${model.modelId}`);
}

async function showEventDefs() {
  try {
    eventDefinitions.value = await fetchJson(eventDefinitionsFile);
    eventDefsVisible.value = true;
  } catch (err) {
    log(`加载事件定义失败: ${err.message}`);
  }
}

log('选矿服务TCP指令工具 已就绪');
log('请先启动 server.py，然后点击「连接」');
</script>
