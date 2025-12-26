import { apiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function getEditableEnvKeys() {
  return apiClient.get('/api/settings/editable-env')
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/settings/editable-env');
      }
      throw error;
    });
}

export function getEditableEnvValues() {
  return apiClient.get('/api/settings/env-values')
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/settings/env-values');
      }
      throw error;
    });
}

export function saveEditableEnvValues(data) {
  return apiClient.post('/api/settings/save-env', data)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.post('/settings/save-env', data);
      }
      throw error;
    });
}

export function getGlobalSettings() {
  return apiClient.get('/api/settings/global')
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/settings/global');
      }
      throw error;
    });
}

export function getProviderSettings() {
  return apiClient.get(normalizePath('settings/providers'))
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/settings/providers');
      }
      throw error;
    });
}

export function getSettingsSchema() {
  return apiClient.get(normalizePath('settings/schema'));
}

export function saveSettings(data) {
  return apiClient.post(normalizePath('settings/save-all'), data);
}

export function updateDefaultProvider(data) {
  return apiClient.post('/api/settings/default-provider', data)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.post('/settings/default-provider', data);
      }
      throw error;
    });
}

export function debugEnvConfig() {
  return apiClient.get('/api/debug/env-config')
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/debug/env-config');
      }
      throw error;
    });
}

export function getProvidersMeta() {
  return apiClient.get('/api/settings/providers-meta');
} 