import { apiClient } from './apiClient';

export function getTaskStatus(taskId) {
  if (!taskId) {
    return Promise.reject(new Error("Task ID不能为空"));
  }
  console.log("Querying task status for ID:", taskId);
  return apiClient.get(`/api/tasks/${taskId}`)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        console.error(`Task not found with ID: ${taskId} at /api/tasks/${taskId}`);
        // Propagate the error for the caller to handle (e.g., show specific message)
        return Promise.reject(error); 
      }
      console.error(`Error fetching task status for ${taskId}:`, error);
      throw error;
    });
} 