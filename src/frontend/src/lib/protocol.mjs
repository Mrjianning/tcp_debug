export const EVENT_TYPE_NAMES = {
  0: 'kUnknown',
  1: 'kLog',
  2: 'kState',
  3: 'kCommand',
  4: 'kCustom',
  5: 'kParam',
};

export function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function numberOrDefault(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function getEventTypeLabel(eventType) {
  return EVENT_TYPE_NAMES[eventType] || `eventType=${eventType}`;
}

export function shouldDisplayMessage(msg, hiddenTypes = new Set()) {
  if (!msg || msg._type !== 'json') return true;
  const eventType = Number(msg.data && msg.data.eventType);
  if (!Number.isInteger(eventType)) return true;
  return !hiddenTypes.has(eventType);
}

export function shouldFormatEventType(eventType, formatTypes = new Set()) {
  return Number.isInteger(eventType) && formatTypes.has(eventType);
}

export function formatReceivedLogMessage(
  data,
  formatTypes = new Set(),
  timeStr = new Date().toLocaleTimeString('zh-CN', { hour12: false }),
) {
  const eventType = Number(data && data.eventType);
  const eventLabel = Number.isInteger(eventType) ? `[${getEventTypeLabel(eventType)}] ` : '';
  const jsonText = shouldFormatEventType(eventType, formatTypes)
    ? `\n${JSON.stringify(data, null, 2)}`
    : ` ${JSON.stringify(data)}`;
  return `[${timeStr}] ${eventLabel}接收数据:${jsonText}`;
}

export function isSuccessfulParamReadResponse(data) {
  const params = data && data.params;
  return !!(
    params &&
    params.operationCommand === 5 &&
    params.operationResult === 2 &&
    params.paramType === 1 &&
    params.data &&
    typeof params.data === 'object'
  );
}

export function getAlgorithmBasicParam(receivedData) {
  const algorithmBasicParam = receivedData && receivedData.algorithmBasicParam;
  return algorithmBasicParam && typeof algorithmBasicParam === 'object' ? algorithmBasicParam : null;
}

export function getJectorSystemParam(receivedData) {
  const algorithmBasicParam = getAlgorithmBasicParam(receivedData);
  if (
    algorithmBasicParam &&
    algorithmBasicParam.jectorSystemParam &&
    typeof algorithmBasicParam.jectorSystemParam === 'object'
  ) {
    return algorithmBasicParam.jectorSystemParam;
  }
  const jectorSystemParam = receivedData && receivedData.jectorSystemParam;
  return jectorSystemParam && typeof jectorSystemParam === 'object' ? jectorSystemParam : null;
}

export function setJectorSystemParam(receivedData, jectorSystemParam) {
  const data = receivedData && typeof receivedData === 'object' ? receivedData : {};
  const normalized = normalizeJectorSystemParam(jectorSystemParam);
  const algorithmBasicParam = getAlgorithmBasicParam(data);
  if (algorithmBasicParam) {
    algorithmBasicParam.jectorSystemParam = normalized;
    return data;
  }
  data.jectorSystemParam = normalized;
  return data;
}

export function buildSetParamsFromReceivedData(template, receivedData, jectorSystemOverride = null) {
  const data = cloneJson(template);
  if (!data.params || typeof data.params !== 'object') {
    data.params = {};
  }
  data.params.data = cloneJson(receivedData);
  if (jectorSystemOverride) {
    if (!data.params.data || typeof data.params.data !== 'object') {
      data.params.data = {};
    }
    setJectorSystemParam(data.params.data, jectorSystemOverride);
  }
  return data;
}

export function createDefaultJectorUnit(unitId = -1) {
  return {
    controllerIp: '127.0.0.1',
    controllerPort: 7001,
    mapfiles: [],
    nozzleCount: 0,
    unitId,
    valveRowIndex: 0,
  };
}

export function createDefaultJectorModule(moduleId = 0) {
  return {
    ejectorLayout: 0,
    electricalDelayMs: 0,
    isMergeSignal: 0,
    jectorUnits: [],
    moduleId,
    sprayWhat: 2,
  };
}

export function normalizeJectorSystemParam(jectorSystemParam) {
  const source = jectorSystemParam && typeof jectorSystemParam === 'object' ? cloneJson(jectorSystemParam) : {};
  const modules = Array.isArray(source.jectorModules) ? source.jectorModules : [];
  const normalizedModules = modules.map((module, moduleIndex) => {
    const normalizedModule = Object.assign(createDefaultJectorModule(moduleIndex), module || {});
    const units = Array.isArray(normalizedModule.jectorUnits) ? normalizedModule.jectorUnits : [];
    normalizedModule.jectorUnits = units.map((unit) => Object.assign(createDefaultJectorUnit(), unit || {}));
    return normalizedModule;
  });

  return Object.assign(
    {
      ejectorModuleCount: normalizedModules.length,
      enableSelfCheck: 0,
      maxNozzleCount: 0,
      maxSprayDurationMs: 0,
      minSprayDurationMs: 0,
      valveCloseDelayMs: 0,
    },
    source,
    {
      ejectorModuleCount: normalizedModules.length,
      jectorModules: normalizedModules,
    },
  );
}

export function addJectorModuleToParam(jectorSystemParam) {
  const data = normalizeJectorSystemParam(jectorSystemParam);
  data.jectorModules.push(createDefaultJectorModule(data.jectorModules.length));
  data.ejectorModuleCount = data.jectorModules.length;
  return data;
}

export function removeJectorModuleFromParam(jectorSystemParam, moduleIndex) {
  const data = normalizeJectorSystemParam(jectorSystemParam);
  data.jectorModules.splice(moduleIndex, 1);
  data.ejectorModuleCount = data.jectorModules.length;
  return data;
}

export function addJectorUnitToModule(jectorSystemParam, moduleIndex) {
  const data = normalizeJectorSystemParam(jectorSystemParam);
  const module = data.jectorModules[moduleIndex];
  if (module) {
    module.jectorUnits.push(createDefaultJectorUnit(-1));
  }
  return data;
}

export function removeJectorUnitFromModule(jectorSystemParam, moduleIndex, unitIndex) {
  const data = normalizeJectorSystemParam(jectorSystemParam);
  const module = data.jectorModules[moduleIndex];
  if (module) {
    module.jectorUnits.splice(unitIndex, 1);
  }
  return data;
}

export function updateJectorModuleField(jectorSystemParam, moduleIndex, field, value) {
  const data = normalizeJectorSystemParam(jectorSystemParam);
  const module = data.jectorModules[moduleIndex];
  if (module) {
    module[field] = numberOrDefault(value, module[field]);
  }
  return data;
}

export function updateJectorUnitField(jectorSystemParam, moduleIndex, unitIndex, field, value) {
  if (field === 'unitId') return normalizeJectorSystemParam(jectorSystemParam);
  const data = normalizeJectorSystemParam(jectorSystemParam);
  const unit = data.jectorModules[moduleIndex] && data.jectorModules[moduleIndex].jectorUnits[unitIndex];
  if (unit) {
    unit[field] = field === 'controllerIp' ? String(value) : numberOrDefault(value, unit[field]);
  }
  return data;
}

export function getMapFileDisplayName(mapfile) {
  return mapfile && (mapfile.name || mapfile.fileName || '');
}

export function getMapFileDisplayIndex(mapfile) {
  if (!mapfile) return '';
  if (mapfile.index !== undefined) return String(mapfile.index);
  if (mapfile.mapIndex !== undefined) return String(mapfile.mapIndex);
  return '';
}

export function extractJectorSystemSummary(receivedData) {
  const source = getJectorSystemParam(receivedData);
  if (!source || typeof source !== 'object') return null;
  const normalized = normalizeJectorSystemParam(source);
  const modules = normalized.jectorModules.map((module) => {
    const units = module.jectorUnits.map((unit) => {
      const mapfiles = Array.isArray(unit.mapfiles) ? unit.mapfiles : [];
      return {
        controllerIp: unit.controllerIp,
        controllerPort: unit.controllerPort,
        mapFileIndex1: getMapFileDisplayIndex(mapfiles[0]),
        mapFileIndex2: getMapFileDisplayIndex(mapfiles[1]),
        mapFileName1: getMapFileDisplayName(mapfiles[0]),
        mapFileName2: getMapFileDisplayName(mapfiles[1]),
        nozzleCount: unit.nozzleCount,
        unitId: unit.unitId,
      };
    });
    return {
      electricalDelayMs: module.electricalDelayMs,
      ejectorLayout: module.ejectorLayout,
      isMergeSignal: module.isMergeSignal,
      moduleId: module.moduleId,
      sprayWhat: module.sprayWhat,
      units,
    };
  });
  return {
    moduleCount: modules.length,
    modules,
    raw: normalized,
    totalUnitCount: modules.reduce((sum, module) => sum + module.units.length, 0),
  };
}

export function extractModelListSummary(receivedData) {
  if (!receivedData || typeof receivedData !== 'object') return null;
  const groups = [
    ['检测模型', 'detect', receivedData.detectModelList || []],
    ['分割模型', 'segment', receivedData.segmentModelList || []],
    ['识别模型', 'rec', receivedData.recModelList || []],
  ].map(([title, key, list]) => ({
    key,
    title,
    items: Array.isArray(list)
      ? list.map((item) => {
          const base = item.modelBaseParam || {};
          return {
            modelId: base.modelId,
            modelName: base.modelName || '',
            modelType: base.modelType,
          };
        })
      : [],
  }));
  return {
    groups,
    totalCount: groups.reduce((sum, group) => sum + group.items.length, 0),
  };
}

export function buildDeleteModelCommand(template, model) {
  const data = cloneJson(template);
  if (!data.params || typeof data.params !== 'object') data.params = {};
  if (!data.params.data || typeof data.params.data !== 'object') data.params.data = {};
  data.params.data.modelType = Number(model.modelType);
  data.params.data.modelId = Number(model.modelId);
  return data;
}

export function getMappingPayloadTarget(data) {
  const hasParams = data.params && typeof data.params === 'object';
  const hasParamsData = hasParams && data.params.data && typeof data.params.data === 'object';
  return hasParamsData ? data.params.data : hasParams ? data.params : data;
}

export function applyMappingFileData(template, fileData) {
  const data = cloneJson(template);
  const target = getMappingPayloadTarget(data);
  target.fileName = fileData.name;
  target.fileSize = fileData.size;
  target.base64Data = fileData.base64Data;
  return data;
}

export function applyMappingOutputPath(template, outputPath) {
  const data = cloneJson(template);
  const target = getMappingPayloadTarget(data);
  target.outPutPath = outputPath;
  return data;
}

export function applyModelFileData(template, listName, label, fileData) {
  const data = cloneJson(template);
  const modelList = data.params && data.params.data && data.params.data[listName];
  if (!Array.isArray(modelList) || !modelList[0] || !modelList[0].modelBaseParam) {
    throw new Error(`${label}模板缺少 ${listName}[0].modelBaseParam`);
  }
  const modelBaseParam = modelList[0].modelBaseParam;
  modelBaseParam.modelName = fileData.name;
  modelBaseParam.modelSize = fileData.size;
  modelBaseParam.modelBase64Data = fileData.base64Data;
  return data;
}

export function applyDetectModelFileData(template, fileData) {
  return applyModelFileData(template, 'detectModelList', '检测模型', fileData);
}

export function applySegmentModelFileData(template, fileData) {
  return applyModelFileData(template, 'segmentModelList', '分割模型', fileData);
}

export function applyRecModelFileData(template, fileData) {
  return applyModelFileData(template, 'recModelList', '识别模型', fileData);
}
