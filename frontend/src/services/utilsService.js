// 移除未使用的 apiClient 导入

export function getBaseUrl() {
  // This might not be needed if components don't call it directly
  // Re-implement or adjust if base URL logic needs exposure
  const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isLocalDev ? '' : ''; 
}

export function normalizePath(path) {
  if (!path) return '/api/';
  let cleanPath = path.trim();
  while (cleanPath.startsWith('/')) {
    cleanPath = cleanPath.substring(1);
  }
  if (cleanPath.startsWith('api/')) {
    return '/' + cleanPath;
  }
  return '/api/' + cleanPath;
} 