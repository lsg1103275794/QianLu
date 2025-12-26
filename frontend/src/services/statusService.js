import { apiClient } from './apiClient';
import { normalizePath } from './utilsService';

// 检测Ollama是否在线的特殊函数 (uses fetch)
async function checkOllamaDirectly(endpoint = "http://localhost:11434") {
  try {
    console.log(`尝试直接检查Ollama: ${endpoint}/api/version`);
    const response = await fetch(`${endpoint}/api/version`, {
      method: 'GET',
      mode: 'cors',
      headers: { 'Accept': 'application/json' },
    });
    if (response.ok) {
      const data = await response.json();
      console.log(`Ollama直接检查成功:`, data);
      return { status: true, version: data.version, message: `Ollama 运行中 (版本 ${data.version})` };
    }
    return { status: false, message: "无法获取Ollama版本信息" };
  } catch (error) {
    console.error("直接检查Ollama失败:", error);
    return { status: false, message: error.message };
  }
}

export function getStatus() {
  return apiClient.get(normalizePath('/status'))
    .catch(error => {
      if (error.response && error.response.status === 404) {
        console.log('路径/status不存在，尝试/api/status...');
        return apiClient.get('/api/status');
      }
      throw error;
    })
    .catch(error => {
      console.log('API状态获取失败，返回错误状态', error);
      if (error.isSilent) {
        return {
          data: {
            service_status: '连接失败',
            analyzer_status: '未知',
            available_providers: [],
            environment_validation: {
              valid: false,
              errors: [`无法连接到后端服务: ${error.friendlyMessage || '未知错误'}`],
              warnings: []
            }
          }
        };
      }
      throw error;
    });
}

export async function getProviderStatus(providerName) {
  if (providerName === 'ollama_local') {
    try {
      const apiResponse = await apiClient.get(`/api/provider-status/${providerName}`)
        .catch(err => {
          if (err.response && err.response.status === 404) return apiClient.get(`/provider-status/${providerName}`);
          throw err;
        });
      if (!apiResponse.data.is_configured || apiResponse.data.connection_test === 'error') {
        const settingsResponse = await apiClient.get('/api/settings/providers')
           .catch(err => {
             if (err.response && err.response.status === 404) return apiClient.get('/settings/providers');
             throw err;
           });
        const ollamaConfig = settingsResponse.data?.ollama_local;
        const ollamaEndpoint = ollamaConfig?.OLLAMA_API_BASE_URL || "http://localhost:11434";
        const directCheck = await checkOllamaDirectly(ollamaEndpoint);
        if (directCheck.status) {
          return {
            data: {
              is_configured: false,
              connection_test: 'success', direct_check: true,
              status_message: `Ollama运行中但未在后端配置: ${directCheck.message}`, model_info: null
            }
          };
        }
      }
      return apiResponse;
    } catch (error) {
      const directCheck = await checkOllamaDirectly();
      if (directCheck.status) {
        return {
          data: {
            is_configured: false, connection_test: 'warning', direct_check: true,
            status_message: `Ollama运行中但未连接到后端: ${directCheck.message}`, model_info: null
          }
        };
      }
      if (error.isSilent) {
        return { data: { is_configured: false, connection_test: 'error', status_message: `连接失败: ${error.friendlyMessage || '无法获取状态'}` } };
      }
      throw error;
    }
  } else {
    return apiClient.get(`/api/provider-status/${providerName}`)
      .catch(error => {
        if (error.response && error.response.status === 404) return apiClient.get(`/provider-status/${providerName}`);
        throw error;
      })
      .catch(error => {
        if (error.isSilent) {
          return { data: { is_configured: false, connection_test: 'error', status_message: `连接失败: ${error.friendlyMessage || '无法获取状态'}` } };
        }
        throw error;
      });
  }
}

export async function pingBackend() {
  try {
    const endpoints = ['/api/status', '/status', '/api/providers', '/providers'];
    let lastError = null;
    const baseUrl = ''; // Assuming relative path works
    
    for (const endpoint of endpoints) {
      try {
        console.log(`尝试ping后端: ${endpoint}`);
        const startTime = Date.now();
        const response = await fetch(baseUrl + endpoint, {
          method: 'GET',
          headers: { 'Accept': 'application/json' },
          signal: AbortSignal.timeout(2000)
        });
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        if (response.ok) {
          return { status: 'success', message: `后端服务可用 (${responseTime}ms)`, details: { endpoint, responseTime, statusCode: response.status } };
        }
        lastError = { endpoint, statusCode: response.status, statusText: response.statusText, responseTime };
      } catch (err) {
        lastError = { endpoint, error: err.message || String(err) };
      }
    }
    return { status: 'error', message: '后端服务不可用', details: { lastError, suggestions: ['检查后端服务是否启动', '检查网络连接', '检查服务端口'] } };
  } catch (error) {
    return { status: 'error', message: `检测失败: ${error.message}`, details: { error: String(error) } };
  }
} 