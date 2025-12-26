import { apiClient, longRunningApiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function getProviders() {
  console.log("Calling getProviders API");
  return apiClient.get(normalizePath('/providers'));
}

export function getModels(providerName) {
  console.log(`[api.getModels] Received request to get models for provider: ${providerName}`);
  const timestamp = new Date().getTime();
  return apiClient.get(`/api/models/${providerName}?_t=${timestamp}`)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        console.log(`路径/api/models/${providerName}未找到，尝试备用路径/api/providers/models/${providerName}`);
        return apiClient.get(`/api/providers/models/${providerName}?_t=${timestamp}`);
      }
      throw error;
    });
}

export function testModelConnection(data) {
  return longRunningApiClient.post('/api/provider/test-model', data)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return longRunningApiClient.post('/provider/test-model', data);
      }
      throw error;
    });
}

export function addApiProvider(data) {
  return apiClient.post('/api/settings/add-provider', data)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.post('/settings/add-provider', data);
      }
      throw error;
    });
} 