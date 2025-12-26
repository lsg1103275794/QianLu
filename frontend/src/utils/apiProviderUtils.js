/**
 * API提供商相关工具函数
 */

/**
 * 检查字段是否为敏感信息
 */
export function isSensitiveKey(key) {
  return key.includes('API_KEY') || key.includes('SECRET') || key.includes('TOKEN');
}

/**
 * 获取标准化的提供商前缀
 */
export function getNormalizedPrefix(providerName) {
  if (!providerName) return '';
  
  // 特殊处理
  const specialCases = {
    'ollama_local': 'OLLAMA',
    'deepseek_ai': 'DEEPSEEK',
    'google_gemini': 'GOOGLE',
    'zhipu_ai': 'ZHIPU',
    'silicon_flow': 'SILICONFLOW',
    'volc_engine': 'VOLC'
  };
  
  return specialCases[providerName] || providerName.toUpperCase();
}

/**
 * 检查是否为模型参数
 */
export function isModelParam(key) {
  if (!key) return false;
  
  const modelParams = ['TEMPERATURE', 'MAX_TOKENS', 'TOP_P', 'TOP_K', 
                       'FREQUENCY_PENALTY', 'PRESENCE_PENALTY', 
                       'REPEAT_PENALTY', 'STREAM'];
                       
  return modelParams.some(param => key.includes(param));
}

/**
 * 检查提供商是否支持TOP_P参数
 */
export function hasTopPSetting(providerName) {
  const unsupportedProviders = []; // 填入不支持TOP_P的提供商
  return !unsupportedProviders.includes(providerName);
}

/**
 * 获取带emoji的提供商名称
 */
export function getProviderWithEmoji(provider) {
  if (!provider || !provider.name) return '🔌 未知提供商';
  
  const emojis = {
    'ollama_local': '🦙',
    'google_gemini': '🌌',
    'openai': '🧠',
    'zhipu_ai': '🧩',
    'deepseek_ai': '🔍',
    'volc_engine': '🌋',
    'silicon_flow': '🔄'
  };
  
  const emoji = emojis[provider.name] || '🤖';
  return `${emoji} ${provider.display_name || provider.name}`;
}

/**
 * 获取提供商状态样式类
 */
export function getProviderStatusClass(status) {
  if (!status) return '';
  
  if (status === 'connected') return 'status-connected';
  if (status === 'error') return 'status-error';
  if (status === 'pending') return 'status-pending';
  
  return '';
}

/**
 * 获取配置项标签
 */
export function getKeyLabel(providerName, key) {
  // 移除前缀
  const prefix = getNormalizedPrefix(providerName);
  let cleanKey = key;
  
  if (key.startsWith(prefix + '_')) {
    cleanKey = key.substring(prefix.length + 1);
  }
  
  // 常见配置项标签映射
  const labelMap = {
    'API_KEY': 'API密钥',
    'API_BASE_URL': 'API基础URL',
    'ENDPOINT': '端点地址',
    'DEFAULT_MODEL': '默认模型',
    'TEMPERATURE': '温度',
    'MAX_TOKENS': '最大输出长度',
    'TOP_P': 'Top P值',
    'TOP_K': 'Top K值',
    'FREQUENCY_PENALTY': '频率惩罚',
    'PRESENCE_PENALTY': '存在惩罚',
    'REPEAT_PENALTY': '重复惩罚',
    'STREAM': '流式输出'
  };
  
  return labelMap[cleanKey] || cleanKey;
}

/**
 * 获取提供商默认设置
 */
export function getDefaultProviderSettings(providerName) {
  switch (providerName) {
    case 'ollama_local':
      return {
        OLLAMA_API_BASE_URL: 'http://localhost:11434',
        OLLAMA_DEFAULT_MODEL: 'gemma3:12b'
      };
    case 'volc_engine':
      return {
        VOLC_ENDPOINT: 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        VOLC_DEFAULT_MODEL: 'ep-20250315081938-jpk8t',
        VOLC_API_KEY: '********'
      };
    case 'silicon_flow':
      return {
        SILICONFLOW_ENDPOINT: 'https://api.siliconflow.cn/v1',
        SILICONFLOW_DEFAULT_MODEL: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B',
        SILICONFLOW_API_KEY: '********',
        SILICONFLOW_TEMPERATURE: '0.7',
        SILICONFLOW_MAX_TOKENS: '2048'
      };
    case 'google_gemini':
      return {
        GOOGLE_DEFAULT_MODEL: 'gemini-1.5-flash-latest',
        GOOGLE_API_KEY: '********',
        GOOGLE_TEMPERATURE: '0.7',
        GOOGLE_MAX_TOKENS: '2048'
      };
    default: {
      const prefix = providerName.toUpperCase();
      return {
        [`${prefix}_API_KEY`]: '********',
        [`${prefix}_ENDPOINT`]: '',
        [`${prefix}_DEFAULT_MODEL`]: '',
        [`${prefix}_TEMPERATURE`]: '0.7',
        [`${prefix}_MAX_TOKENS`]: '2048'
      };
    }
  }
}

/**
 * 合并冗余配置项
 */
export function mergeRedundantConfigs(providerName, config) {
  if (!providerName || !config) return config;
  
  const configCopy = { ...config };
  
  // 处理硅基流动的API_BASE_URL和ENDPOINT冗余
  if (providerName === 'silicon_flow') {
    // 如果两者都存在，保留ENDPOINT
    if (configCopy.SILICONFLOW_API_BASE_URL && configCopy.SILICONFLOW_ENDPOINT) {
      configCopy.SILICONFLOW_ENDPOINT = configCopy.SILICONFLOW_ENDPOINT || configCopy.SILICONFLOW_API_BASE_URL;
      delete configCopy.SILICONFLOW_API_BASE_URL;
    }
    // 如果只有API_BASE_URL, 则改用ENDPOINT
    else if (configCopy.SILICONFLOW_API_BASE_URL) {
      configCopy.SILICONFLOW_ENDPOINT = configCopy.SILICONFLOW_API_BASE_URL;
      delete configCopy.SILICONFLOW_API_BASE_URL;
    }
    
    // 处理MODEL和DEFAULT_MODEL冗余
    if (configCopy.SILICONFLOW_MODEL && configCopy.SILICONFLOW_DEFAULT_MODEL) {
      configCopy.SILICONFLOW_DEFAULT_MODEL = configCopy.SILICONFLOW_DEFAULT_MODEL || configCopy.SILICONFLOW_MODEL;
      delete configCopy.SILICONFLOW_MODEL;
    }
    else if (configCopy.SILICONFLOW_MODEL) {
      configCopy.SILICONFLOW_DEFAULT_MODEL = configCopy.SILICONFLOW_MODEL;
      delete configCopy.SILICONFLOW_MODEL;
    }
  }
  
  // 处理Ollama的MODEL和DEFAULT_MODEL冗余
  if (providerName === 'ollama_local') {
    if (configCopy.OLLAMA_MODEL && configCopy.OLLAMA_DEFAULT_MODEL) {
      configCopy.OLLAMA_DEFAULT_MODEL = configCopy.OLLAMA_DEFAULT_MODEL || configCopy.OLLAMA_MODEL;
      delete configCopy.OLLAMA_MODEL;
    }
    else if (configCopy.OLLAMA_MODEL) {
      configCopy.OLLAMA_DEFAULT_MODEL = configCopy.OLLAMA_MODEL;
      delete configCopy.OLLAMA_MODEL;
    }
  }
  
  return configCopy;
}

/**
 * 初始化模型参数默认值
 */
export function initializeModelParams(providerName, config) {
  const configCopy = { ...config };
  
  // 检查是否有任何模型参数
  const hasAnyModelParam = Object.keys(configCopy).some(key => 
    isModelParam(key) && configCopy[key] !== null && configCopy[key] !== undefined && configCopy[key] !== '');
  
  const prefix = getNormalizedPrefix(providerName);
  const tempKey = `${prefix}_TEMPERATURE`;
  const tokensKey = `${prefix}_MAX_TOKENS`;
  const topPKey = `${prefix}_TOP_P`;

  // 设置默认值
  if (!(tempKey in configCopy) || configCopy[tempKey] === null || configCopy[tempKey] === undefined || configCopy[tempKey] === '') {
    configCopy[tempKey] = 0.7;
  }
  
  if (!(tokensKey in configCopy) || configCopy[tokensKey] === null || configCopy[tokensKey] === undefined || configCopy[tokensKey] === '') {
    configCopy[tokensKey] = 2048;
  }
  
  if (hasTopPSetting(providerName) && (!(topPKey in configCopy) || configCopy[topPKey] === null || configCopy[topPKey] === undefined || configCopy[topPKey] === '')) {
    configCopy[topPKey] = 0.9;
  }
  
  return {
    configCopy,
    hasModelParams: hasAnyModelParam
  };
}

export default {
  isSensitiveKey,
  getNormalizedPrefix,
  isModelParam,
  hasTopPSetting,
  getProviderWithEmoji,
  getProviderStatusClass,
  getKeyLabel,
  getDefaultProviderSettings,
  mergeRedundantConfigs,
  initializeModelParams
}; 