import { apiClient, longRunningApiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function getAnalysisReports() {
  return apiClient.get('/api/analysis-reports')
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/analysis-reports');
      }
      throw error;
    });
}

export function analyzeText(data) {
  return longRunningApiClient.post(normalizePath('analysis/analyze'), data);
}

export function analyzeTextAsync(data) {
  console.log("提交异步分析请求:", data);
  return longRunningApiClient.post(normalizePath('analysis/analyze/async'), data)
    .then(response => {
      console.log("异步任务提交成功，响应:", response.data);
      if (response.data.task_id) console.log("任务ID:", response.data.task_id);
      if (response.data.task_endpoint) console.log("API返回了任务查询端点:", response.data.task_endpoint);
      return response;
    })
    .catch(error => {
      if (error.response && error.response.status === 404) {
        console.log("API路径/api/analysis/analyze/async不存在，尝试备用路径...");
        return longRunningApiClient.post('/api/analyze/async', data);
      }
      throw error;
    })
    .catch(error => {
      console.error("所有异步分析API路径尝试失败:", error);
      throw error;
    });
}

export function getTemplates() {
  return apiClient.get('/api/analysis/templates');
}

export function getTemplateDetails(templateId) {
  if (!templateId) return Promise.reject(new Error("Template ID cannot be empty"));
  const url = `/api/analysis/templates/${encodeURIComponent(templateId)}`;
  console.log(`Fetching template details from: ${url}`);
  return apiClient.get(url);
}

export function getLiteratureTemplate() {
  return apiClient.get('/api/analysis/templates/literary_analysis');
}

export function getDetailedLiteratureTemplateStructure() {
  return apiClient.get('/api/literature-analysis/template-structure');
}

export function analyzeLiterature(data) {
  return longRunningApiClient.post('/api/literature-analysis/analyze', data);
}

// Note: saveAnalysisResult seems generic, might belong elsewhere or be split
// Keeping it here for now as it relates to analysis flow
export function saveAnalysisResult(data) {
  return apiClient.post('/api/save/analysis-result', data)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.post('/save/analysis-result', data);
      }
      throw error;
    });
}

export function getTextAnalysisReports() {
  return apiClient.get(normalizePath('results/list-text-analysis'));
}

export function getTextAnalysisResult(reportId) {
  return apiClient.get(normalizePath(`results/text-analysis/${reportId}`));
}

export function getLiteratureAnalysisResult(reportId) {
  return apiClient.get(normalizePath(`results/literature/${reportId}`));
}

export function getAllAnalysisResults() {
  return apiClient.get(normalizePath('results/list-all'));
}

export function saveTextAnalysisResult(data) {
  return apiClient.post(normalizePath('results/save-text-analysis'), data);
}

export function saveLiteratureAnalysisResult(data) {
  return apiClient.post('/api/results/save-literature', data);
}

export function clearAnalysisResults(moduleType = 'all') {
  return apiClient.delete(normalizePath(`results/clear?module=${moduleType}`));
} 