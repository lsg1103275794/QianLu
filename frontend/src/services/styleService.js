import { apiClient, longRunningApiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function transferStyle(data) {
  return longRunningApiClient.post('/api/transfer', data)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return longRunningApiClient.post('/transfer', data);
      }
      throw error;
    });
}

export function performStyleTransfer(inputType, newTheme, provider, model, sourceText, analysisReportId) {
  const payload = {
    input_type: inputType,
    new_theme: newTheme,
    provider: provider,
    model: model,
    source_text: sourceText,
    analysis_report_id: analysisReportId
  };
  console.log('Sending performStyleTransfer payload:', payload);
  return longRunningApiClient.post(normalizePath('transfer/'), payload);
}

export function getStyleTransferResults() {
  return apiClient.get(normalizePath('results/list-style'));
}

export function getStyleTransferResult(reportId) {
  return apiClient.get(normalizePath(`results/style/${reportId}`));
}

export function saveStyleTransferResult(data) {
  return apiClient.post(normalizePath('results/save-style'), data);
} 