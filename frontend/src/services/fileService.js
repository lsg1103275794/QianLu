import { apiClient, longRunningApiClient } from './apiClient';
import { normalizePath } from './utilsService';

export function uploadFile(file, onUploadProgress) {
  const formData = new FormData();
  formData.append('file', file);
  return longRunningApiClient.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress 
  })
  .catch(error => {
    if (error.response && error.response.status === 404) {
      return longRunningApiClient.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress
      });
    }
    throw error;
  });
}

export function uploadAndExtractText(fileOrFormData, onUploadProgress) {
  let formData;
  if (fileOrFormData instanceof FormData) {
    formData = fileOrFormData;
  } else {
    formData = new FormData();
    formData.append('file', fileOrFormData);
  }
  
  const config = { headers: { 'Content-Type': 'multipart/form-data' } };
  if (typeof onUploadProgress === 'function') {
    config.onUploadProgress = onUploadProgress;
  }
  
  return longRunningApiClient.post('/api/files/upload-and-extract', formData, config);
}

export function getFileContentFromServer(filePath) {
  console.log(`Calling getFileContentFromServer API for path: ${filePath}`);
  return apiClient.get(normalizePath(`/files/file-content?file_path=${encodeURIComponent(filePath)}`), {
    responseType: 'text' // Ensure Axios treats the response as text
  });
}

// Alias or potentially distinct function if backend differs
export function getFileContent(filePath) {
  console.log(`Calling getFileContent API for path: ${filePath}`);
  return apiClient.get(normalizePath(`/files/file-content?file_path=${encodeURIComponent(filePath)}`), {
    responseType: 'text'
  });
} 