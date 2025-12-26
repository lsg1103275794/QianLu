import { apiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function getResults(params = {}) {
  return apiClient.get(normalizePath('results'), { params });
}

export function renameResult(resultId, newName) {
  // This is the function causing the 405 Method Not Allowed error.
  // The frontend uses PATCH, the backend needs to support it for this route.
  return apiClient.patch(normalizePath(`results/${resultId}/rename`), { new_name: newName });
}

export function deleteResult(resultId) {
  return apiClient.delete(normalizePath(`results/${resultId}`));
}

export function getResultDetails(resultId) {
  return apiClient.get(normalizePath(`results/${resultId}`));
}

export function updateResultContent(resultId, newContent) {
  // Check if backend supports this PATCH method
  console.warn('updateResultContent is called, ensure backend supports PATCH /api/results/:id/content');
  return apiClient.patch(normalizePath(`results/${resultId}/content`), { content: newContent });
}

// Function to save a potentially edited result as a NEW analysis entry
// Corresponds to POST /api/results/save-text-analysis or /save-literature
// Adjust endpoint based on backend implementation (or if a unified endpoint exists)
export function saveNewAnalysisResult(payload) {
  // Determine endpoint based on payload.analysis_type or use a unified endpoint
  let endpoint = 'results/save-text-analysis'; // Default or determine dynamically
  if (payload.analysis_type && payload.analysis_type.startsWith('literature')) {
    endpoint = 'results/save-literature';
  } else if (payload.analysis_type && payload.analysis_type === 'style') {
     endpoint = 'results/save-style'; // Or handle style saving separately
     console.warn('Attempting to save style result via saveNewAnalysisResult, consider dedicated function');
  }
  // TODO: Ensure payload structure matches backend SaveAnalysisPayload model
  console.log(`[resultsService] Calling POST ${normalizePath(endpoint)} with payload:`, payload);
  return apiClient.post(normalizePath(endpoint), payload);
} 