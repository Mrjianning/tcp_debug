const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const projectRoot = path.resolve(__dirname, '..');
const readText = (...parts) => fs.readFileSync(path.join(projectRoot, ...parts), 'utf8');
const readJson = (...parts) => JSON.parse(readText(...parts));
const exists = (...parts) => fs.existsSync(path.join(projectRoot, ...parts));

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(exists('package.json'), 'project should define a frontend package.json');
assert(!exists('src', 'index.html'), 'legacy src/index.html should be removed after Vue migration');
assert(!exists('src', 'styles.css'), 'legacy src/styles.css should be removed after Vue migration');
assert(exists('src', 'frontend', 'index.html'), 'Vue app should have src/frontend/index.html');
assert(exists('src', 'frontend', 'vite.config.js'), 'Vue app should have src/frontend/vite.config.js');
assert(exists('src', 'frontend', 'src', 'main.js'), 'Vue app should have src/frontend/src/main.js');
assert(exists('src', 'frontend', 'src', 'App.vue'), 'Vue app should have src/frontend/src/App.vue');
assert(exists('src', 'frontend', 'src', 'lib', 'protocol.mjs'), 'protocol helpers should be isolated in src/frontend/src/lib/protocol.mjs');
for (const componentFile of [
  'AppHeader.vue',
  'CommandPalette.vue',
  'EventDefinitionsModal.vue',
  'JectorModal.vue',
  'JsonEditorPanel.vue',
  'LogControls.vue',
  'ModelListModal.vue',
  'NetworkManagerModal.vue',
  'TerminalLogPanel.vue',
]) {
  assert(
    exists('src', 'frontend', 'src', 'components', componentFile),
    `Vue UI should split ${componentFile} into src/frontend/src/components`,
  );
}

const packageJson = readJson('package.json');
for (const dep of ['@vitejs/plugin-vue', 'vite', 'vue', 'naive-ui']) {
  assert(
    packageJson.dependencies?.[dep] || packageJson.devDependencies?.[dep],
    `package.json should depend on ${dep}`,
  );
}
assert(packageJson.scripts?.build === 'vite build --config src/frontend/vite.config.js', 'package.json should expose the Vite build script');
assert(packageJson.scripts?.test?.includes('tests/test_frontend.js'), 'package.json should run the frontend architecture test');

const appVue = readText('src', 'frontend', 'src', 'App.vue');
const componentDir = path.join(projectRoot, 'src', 'frontend', 'src', 'components');
const vueSource = [
  appVue,
  ...fs.readdirSync(componentDir)
    .filter((name) => name.endsWith('.vue'))
    .map((name) => readText('src', 'frontend', 'src', 'components', name)),
].join('\n');
for (const component of ['NConfigProvider', 'NButton', 'NCard', 'NInput', 'NModal', 'NDataTable', 'NCheckbox']) {
  assert(vueSource.includes(component), `Vue UI should use Naive UI component ${component}`);
}
assert(appVue.includes('NDialogProvider'), 'App.vue should provide Naive UI dialog support');
assert(appVue.includes('createDiscreteApi'), 'App.vue should use Naive UI discrete feedback APIs');
for (const title of ['选矿服务 TCP 调试台', '自定义 JSON', '日志输出', '喷阀模块管理', '模型列表', '事件定义', '网络管理']) {
  assert(vueSource.includes(title), `Vue UI should preserve visible section "${title}"`);
}
const networkModalVue = readText('src', 'frontend', 'src', 'components', 'NetworkManagerModal.vue');
for (const label of ['配置', '网口名称', 'IPv4地址', 'MAC地址', '网线状态', '当前Web连接', '目标名称', '静态IP', '配置预览', '应用配置']) {
  assert(networkModalVue.includes(label), `Network manager should show visible field label "${label}"`);
}
assert(networkModalVue.includes('NCheckbox'), 'Network manager should let users choose whether each interface is configured');
assert(networkModalVue.includes(':disabled="item.isActiveWebInterface"'), 'Active web interface configure switch should be locked on');
assert(networkModalVue.includes(':disabled="!item.configureEnabled || item.isActiveWebInterface"'), 'Active web interface name and IP should be read-only');
assert(appVue.includes('configureEnabled: Boolean(item.configureEnabled ?? (item.linkDetected && item.ipv4Address))'), 'connected interfaces with IPv4 should be enabled by default');
assert(appVue.includes('networkInterfaces.value.filter((item) => item.configureEnabled)'), 'network preview and apply should submit only enabled interfaces');
for (const endpoint of ['/api/network/interfaces', '/api/network/preview', '/api/network/apply']) {
  assert(appVue.includes(endpoint), `App.vue should call ${endpoint}`);
}
assert(appVue.includes('message.loading'), 'network apply should show an in-progress message');
assert(appVue.includes('message.success'), 'network apply should show success feedback');
assert(appVue.includes('message.error'), 'network apply should show failure feedback');
assert(appVue.includes('dialog.success'), 'network apply success should open a result dialog');
assert(appVue.includes('dialog.error'), 'network apply failure should open a result dialog');
const jectorModalVue = readText('src', 'frontend', 'src', 'components', 'JectorModal.vue');
for (const label of ['打击类型', '喷阀布局', '合并信号', '电气延迟', '单元ID', '控制器IP', '控制器端口', '喷嘴数量', 'map文件', '操作']) {
  assert(jectorModalVue.includes(label), `Jector modal should show visible field label "${label}"`);
}
for (const fieldName of ['sprayWhat', 'ejectorLayout', 'isMergeSignal', 'electricalDelayMs']) {
  assert(jectorModalVue.includes(`<small>${fieldName}</small>`), `Jector modal should show raw field name ${fieldName}`);
}
for (const componentName of [
  'AppHeader',
  'CommandPalette',
  'LogControls',
  'JsonEditorPanel',
  'TerminalLogPanel',
  'JectorModal',
  'ModelListModal',
  'NetworkManagerModal',
  'EventDefinitionsModal',
]) {
  assert(appVue.includes(componentName), `App.vue should compose ${componentName}`);
}
assert(appVue.includes('class="ubuntu-shell"'), 'App.vue should use Ubuntu shell layout');
assert(vueSource.includes(''), '');
assert(!vueSource.includes('工业控制调试工作站'), 'old industrial chrome copy should be removed');
for (const template of [
  'json/startSorting.json',
  'json/stopSorting.json',
  'json/getParams.json',
  'json/setParams.json',
  'json/mappingImportTemplate.json',
  'json/mappingExportTemplate.json',
  'json/dualAvgExportTemplate.json',
  'json/getModelList.json',
  'json/addDetectModelTemplate.json',
  'json/addSegmentModelTemplate.json',
  'json/addRecModelTemplate.json',
]) {
  assert(appVue.includes(template), `Vue app should keep template reference ${template}`);
}
assert(appVue.includes('/api/choose-directory'), 'export path buttons should request the backend directory picker');
assert(appVue.includes('chooseDirectoryPath'), 'frontend should isolate directory picker request in chooseDirectoryPath');
assert(!appVue.includes('window.prompt'), 'export path buttons should not use prompt after directory picker support');
assert(appVue.includes('/api/json/update-set-params'), 'parameter reads should persist actual params to setParams.json');
assert(appVue.includes('saveSetParamsTemplate'), 'frontend should isolate setParams.json persistence in saveSetParamsTemplate');

const themeCss = readText('src', 'frontend', 'src', 'theme.css');
for (const expected of [
  '--ubuntu-orange',
  '--ubuntu-aubergine',
  '--ubuntu-warm-gray',
  '--terminal-bg',
  '--terminal-purple',
  '.ubuntu-shell',
  '.ubuntu-topbar',
  '.ubuntu-card',
  '.ubuntu-workspace',
  '.terminal-window',
  '.terminal-titlebar',
]) {
  assert(themeCss.includes(expected), `Ubuntu theme should define ${expected}`);
}
assert(!themeCss.includes('--steel-bg'), 'old industrial steel theme variables should be removed');
assert(!themeCss.includes('.industrial-card'), 'old industrial card class should be removed');
assert(/html,\s*body,\s*#app\s*\{[\s\S]*height\s*:\s*100%/.test(themeCss), 'root elements should have fixed viewport height');
assert(/body\s*\{[\s\S]*overflow\s*:\s*hidden/.test(themeCss), 'page body should not scroll; panels should scroll internally');
assert(/\.ubuntu-shell\s*\{[\s\S]*height\s*:\s*100vh/.test(themeCss), 'Ubuntu shell should lock to viewport height');
assert(/\.ubuntu-workspace\s*\{[\s\S]*grid-template-rows\s*:\s*minmax\(0,\s*1fr\)/.test(themeCss), 'workspace should reserve flexible bounded content area');
assert(/\.json-panel\s*\{[\s\S]*overflow\s*:\s*hidden/.test(themeCss), 'JSON panel should hide outer overflow');
assert(/\.json-editor\s*\{[\s\S]*overflow\s*:\s*hidden/.test(themeCss), 'JSON editor wrapper should not grow the page');
assert(/\.terminal-window\s*\{[\s\S]*overflow\s*:\s*auto/.test(themeCss), 'terminal should scroll internally');
assert(themeCss.includes('.field-cell'), 'Jector module fields should have visible labels');
assert(themeCss.includes('.unit-table-header'), 'Jector unit rows should have a visible header');

const buildBat = readText('scripts', 'build.bat');
const buildSh = readText('scripts', 'build.sh');
for (const expected of ['build\\release\\tcp_debug-win', 'build\\artifacts\\tcp_debug-win', 'start.bat', 'README.txt']) {
  assert(buildBat.includes(expected), `Windows build script should package ${expected}`);
}
for (const expected of ['build/release/tcp_debug-linux', 'build/artifacts/tcp_debug-linux', 'start.sh', 'start-root.sh', 'install-service.sh', 'tcp_debug.service', 'README.txt']) {
  assert(buildSh.includes(expected), `Linux build script should package ${expected}`);
}
assert(buildSh.includes('PYTHON_CMD='), 'Linux build script should store the selected Python command');
assert(buildSh.includes('CONDA_ENV_PREFIX='), 'Linux build script should define a local conda build environment prefix');
assert(buildSh.includes('command -v conda'), 'Linux build script should detect conda before falling back to system Python');
assert(buildSh.includes('conda create -y -p "$CONDA_ENV_PREFIX"'), 'Linux build script should create a local conda build environment when conda is available');
assert(buildSh.includes('command -v python3'), 'Linux build script should prefer python3 when python is unavailable');
assert(buildSh.includes('"$PYTHON_CMD" -m PyInstaller'), 'Linux build script should run PyInstaller with the selected Python command');
for (const releaseOnly of ['%RELEASE_DIR%\\package.json', '%RELEASE_DIR%\\resources', '%RELEASE_DIR%\\python-deps']) {
  assert(!buildBat.includes(releaseOnly), `Windows runtime release should not include ${releaseOnly}`);
}
for (const releaseOnly of ['$RELEASE_DIR/package.json', '$RELEASE_DIR/resources', '$RELEASE_DIR/python-deps']) {
  assert(!buildSh.includes(releaseOnly), `Linux runtime release should not include ${releaseOnly}`);
}
assert(buildBat.includes('ARTIFACTS_DIR'), 'Windows build script should keep debug materials in artifacts');
assert(buildSh.includes('ARTIFACTS_DIR'), 'Linux build script should keep debug materials in artifacts');
assert(buildBat.includes('call npm install'), 'Windows build script should call npm install without terminating the batch file');
assert(buildBat.includes('call npm run build'), 'Windows build script should call npm run build without terminating the batch file');

(async () => {
  const protocolSource = readText('src', 'frontend', 'src', 'lib', 'protocol.mjs');
  const protocol = await import(pathToFileURL(path.join(projectRoot, 'src', 'frontend', 'src', 'lib', 'protocol.mjs')).href);
  for (const fn of [
    'applyMappingFileData',
    'applyMappingOutputPath',
    'applyModelFileData',
    'buildDeleteModelCommand',
    'buildSetParamsFromReceivedData',
    'formatReceivedLogMessage',
    'getJectorSystemParam',
    'normalizeJectorSystemParam',
    'setJectorSystemParam',
    'shouldDisplayMessage',
  ]) {
    assert(typeof protocol[fn] === 'function', `protocol.mjs should export ${fn}`);
  }
  assert(!protocolSource.includes('document.getElementById'), 'protocol helpers should not depend on DOM nodes');

  const mappingTemplate = readJson('src', 'json', 'mappingImportTemplate.json');
  const appliedMapping = protocol.applyMappingFileData(mappingTemplate, {
    name: 'new-map.txt',
    size: 321,
    base64Data: 'QUJD',
  });
  assert(appliedMapping.params.data.fileName === 'new-map.txt', 'mapping file name should be applied to params.data.fileName');
  assert(appliedMapping.params.data.fileSize === 321, 'mapping file size should be applied to params.data.fileSize');
  assert(appliedMapping.params.data.base64Data === 'QUJD', 'mapping base64 should be applied to params.data.base64Data');

  const exportTemplate = readJson('src', 'json', 'mappingExportTemplate.json');
  const appliedOutputPath = protocol.applyMappingOutputPath(exportTemplate, 'D:\\maps\\out');
  assert(appliedOutputPath.params.data.outPutPath === 'D:\\maps\\out', 'output path should be applied to params.data.outPutPath');

  const deleteTemplate = readJson('src', 'json', 'deleteDetectModelTemplate.json');
  const deleteCommand = protocol.buildDeleteModelCommand(deleteTemplate, { modelType: 1, modelId: 1001 });
  assert(deleteCommand.params.paramType === 23, 'delete command should keep model delete paramType');
  assert(deleteCommand.params.data.modelType === 1, 'delete command should fill modelType');
  assert(deleteCommand.params.data.modelId === 1001, 'delete command should fill modelId');

  const compactLog = protocol.formatReceivedLogMessage(
    { eventType: 3, params: { operationCommand: 5 } },
    new Set(),
    '11:20:43',
  );
  assert(compactLog.includes('[11:20:43] [kCommand] 接收数据: {'), 'compact log should include event label and JSON');
  assert(!compactLog.includes('\n  "params"'), 'compact log should not pretty-print unselected event types');

  const prettyLog = protocol.formatReceivedLogMessage(
    { eventType: 3, params: { operationCommand: 5 } },
    new Set([3]),
    '11:20:43',
  );
  assert(prettyLog.includes('\n  "params": {'), 'selected event types should pretty-print JSON');

  assert(!protocol.shouldDisplayMessage({ _type: 'json', data: { eventType: 4 } }, new Set([4])), 'hidden event types should be filtered');
  assert(protocol.shouldDisplayMessage({ _type: 'system', msg: '连接成功' }, new Set([4])), 'system messages should always display');

  const newParamData = {
    algorithmBasicParam: {
      imageEngine: 'XrayEngine(High)',
      jectorSystemParam: {
        enableSelfCheck: 1,
        maxNozzleCount: 512,
        jectorModules: [
          {
            moduleId: 0,
            sprayWhat: 0,
            jectorUnits: [{ unitId: 1, controllerIp: '192.168.3.88', controllerPort: 5000 }],
          },
        ],
      },
    },
  };
  const oldParamData = {
    jectorSystemParam: {
      enableSelfCheck: 0,
      jectorModules: [{ moduleId: 1, sprayWhat: 2, jectorUnits: [] }],
    },
  };
  assert(protocol.getJectorSystemParam(newParamData).enableSelfCheck === 1, 'new param structure should expose nested jectorSystemParam');
  assert(protocol.getJectorSystemParam(oldParamData).enableSelfCheck === 0, 'old param structure should still expose top-level jectorSystemParam');

  const editedJectorSystem = {
    enableSelfCheck: 0,
    maxNozzleCount: 128,
    jectorModules: [{ moduleId: 9, sprayWhat: 2, jectorUnits: [] }],
  };
  const newApplied = protocol.buildSetParamsFromReceivedData({ params: { data: {} } }, newParamData, editedJectorSystem);
  assert(
    newApplied.params.data.algorithmBasicParam.jectorSystemParam.maxNozzleCount === 128,
    'new param structure should write edited jectorSystemParam under algorithmBasicParam',
  );
  assert(
    !Object.prototype.hasOwnProperty.call(newApplied.params.data, 'jectorSystemParam'),
    'new param structure should not create legacy top-level jectorSystemParam when nested location exists',
  );
  const oldApplied = protocol.buildSetParamsFromReceivedData({ params: { data: {} } }, oldParamData, editedJectorSystem);
  assert(oldApplied.params.data.jectorSystemParam.maxNozzleCount === 128, 'old param structure should keep writing top-level jectorSystemParam');

  console.log('Frontend Vue migration tests OK');
})();
