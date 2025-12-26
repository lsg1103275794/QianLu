import axios from 'axios';
import { ElMessage } from 'element-plus';

// 根据环境自动检测基础URL
function getBaseUrlFromEnvironment() {
  const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocalDev) {
    console.log('API服务 (default): 开发环境，使用同源API基础URL (通常为空)');
    return ''; // 保持原有逻辑，供不需要强制代理的客户端使用
  }
  console.log('API服务 (default): 生产环境，使用同源API基础URL (通常为空)');
  return ''; 
}

const API_BASE_URL = getBaseUrlFromEnvironment();

// 创建标准的API客户端（用于普通请求）
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000, // 45 seconds
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store',
    'Pragma': 'no-cache',
    'Expires': '0'
  }
});

export const longRunningApiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1800000, // 30分钟
  headers: { 'Content-Type': 'application/json' },
});

// --- 新增：为需要走代理的API（如研报生成）创建一个特定配置的客户端 ---
export const proxyApiClient = axios.create({
  baseURL: '/api', // 固定使用 /api 前缀，依赖 vue.config.js 中的代理设置
  timeout: 60000, // 可以设置一个合适的超时时间，例如60秒
  headers: {
    'Content-Type': 'application/json',
    // 可以根据需要添加其他特定头部
  }
});

// 为每个请求添加时间戳以防止缓存 (应用于 apiClient)
apiClient.interceptors.request.use(config => {
  if (config.method === 'get') {
    config.params = config.params || {};
    config.params['_t'] = new Date().getTime();
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// (应用于 longRunningApiClient)
longRunningApiClient.interceptors.request.use(config => {
  console.log(`长时请求: ${config.method.toUpperCase()} ${config.url}`, config);
   if (config.method.toLowerCase() === 'get') {
    config.params = { ...config.params, _t: new Date().getTime() };
  }
  return config;
}, error => Promise.reject(error));

// (可选) 为 proxyApiClient 也应用请求拦截器，例如添加时间戳
proxyApiClient.interceptors.request.use(config => {
  if (config.method === 'get') {
    config.params = config.params || {};
    config.params['_t'] = new Date().getTime(); 
  }
  console.log(`代理请求 (proxyApiClient): ${config.method.toUpperCase()} ${config.baseURL}${config.url}`, config.data);
  return config;
}, error => {
  return Promise.reject(error);
});


// 创建通用响应拦截器逻辑
function createResponseInterceptorLogic(clientName = 'default') { // 添加一个参数以区分日志
  return {
    onFulfilled: response => {
      console.log(`响应 (${clientName}): ${response.status} ${response.config.baseURL}${response.config.url}`, response.data);
      return response;
    },
    onRejected: error => {
      console.error(`响应错误 (${clientName}): ${error.config?.baseURL || ''}${error.config?.url || '未知URL'}`, error);
      let message = '请求失败';
      if (error.response) {
        console.error(`服务器返回错误 ${error.response.status}: ${error.config?.baseURL || ''}${error.config?.url}`, error.response.data);
        message = `服务器错误: ${error.response.data?.detail || error.response.data || error.response.status}`;
      } else if (error.request) {
        message = error.code === 'ECONNABORTED' ? '请求超时' : '无法连接服务器';
      } else {
        message = error.message;
      }

      const isSilentError = error.config && 
        (error.config.url.includes('/status') || 
         error.config.url.includes('/provider-status') || 
         error.config.url.includes('/tasks/') );

      if (isSilentError) {
        console.error(`静默处理API错误 (${clientName}):`, message);
        return Promise.reject({ ...error, isSilent: true, friendlyMessage: message });
      } else {
        ElMessage.error(message);
      }
      return Promise.reject(error);
    }
  };
}

// 应用响应拦截器
const defaultInterceptorLogic = createResponseInterceptorLogic('apiClient');
apiClient.interceptors.response.use(defaultInterceptorLogic.onFulfilled, defaultInterceptorLogic.onRejected);

const longRunningInterceptorLogic = createResponseInterceptorLogic('longRunningApiClient');
longRunningApiClient.interceptors.response.use(longRunningInterceptorLogic.onFulfilled, longRunningInterceptorLogic.onRejected);

// 为 proxyApiClient 应用响应拦截器
const proxyInterceptorLogic = createResponseInterceptorLogic('proxyApiClient');
proxyApiClient.interceptors.response.use(proxyInterceptorLogic.onFulfilled, proxyInterceptorLogic.onRejected);

// 注意：longRunningApiClient 已经是命名导出了，所以这里不需要重复 export { longRunningApiClient }
// apiClient 也已经是命名导出了 