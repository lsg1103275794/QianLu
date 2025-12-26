import { apiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function getUiState(pageKey) {
  if (!pageKey) {
    console.error("getUiState requires a pageKey");
    return Promise.reject("Missing pageKey for getUiState");
  }
  const safeKey = encodeURIComponent(pageKey);
  console.log(`Fetching UI state for key: ${safeKey}`);
  return apiClient.get(normalizePath(`ui-state/${safeKey}`));
}

export function saveUiState(pageKey, state) {
  if (!pageKey) {
    console.error("saveUiState requires a pageKey");
    return Promise.reject("Missing pageKey for saveUiState");
  }
  // Allow saving empty state if needed, or add check here
  // if (!state) { return Promise.reject("State cannot be empty for saveUiState"); }
  const safeKey = encodeURIComponent(pageKey);
  console.log(`Saving UI state for key: ${safeKey}`);
  return apiClient.post(normalizePath(`ui-state/${safeKey}`), state);
} 