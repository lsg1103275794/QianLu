import { proxyApiClient, longRunningApiClient } from './apiClient';
import { normalizePath } from './utilsService';

/**
 * 调用后端API生成研报
 * @param {{ topic: string, model?: string }} payload - 请求体，包含研报主题和可选的模型名称
 * @returns {Promise<Object>} - 包含研报内容的对象或错误信息
 */
export const generateReportAPI = async (payload) => {
  try {
    // 使用 proxyApiClient，它的 baseURL 固定为 '/api'
    // 确保payload中包含 topic 和可选的 model
    const requestData = { topic: payload.topic };
    if (payload.model) {
      requestData.model = payload.model;
    }
    const response = await proxyApiClient.post('/v1/reports/generate-report', requestData);
    return response.data; // FastAPI 通常会将响应数据直接放在 data 属性中
  } catch (error) {
    console.error('Error calling generateReportAPI:', error.response || error.message);
    // 返回更详细的错误信息，以便UI层处理
    throw error.response ? error.response.data : { detail: error.message || '生成研报时发生网络错误' };
  }
};

// New function for Cloud API providers
export function generateCloudReportAPI(data) {
  // Define the new endpoint for cloud generation
  const path = normalizePath('v1/reports/generate/cloud'); 
  console.log(`[reportService] Calling Cloud report endpoint: ${path}`, data);
  // Use longRunningApiClient as cloud APIs can also take time
  return longRunningApiClient.post(path, data)
    .then(response => response.data); // Directly return data on success
}

// Function to fetch saved reports (if applicable)
export function getSavedReports() {
  const path = normalizePath('report-generator/reports');
  console.log(`[reportService] Fetching saved reports from: ${path}`);
  return proxyApiClient.get(path)
    .then(response => response.data);
}

// Function to save a generated report (if applicable)
export function saveReport(reportData) {
   const path = normalizePath('report-generator/save');
   console.log(`[reportService] Saving report to: ${path}`);
   return proxyApiClient.post(path, reportData)
     .then(response => response.data);
} 