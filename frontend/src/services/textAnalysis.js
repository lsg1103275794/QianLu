import api from './api';

/**
 * 文本分析服务
 */
export default {
  /**
   * 执行文本分析
   * @param {Object} params 分析参数
   * @param {string} params.text 要分析的文本内容
   * @param {string} params.provider API提供商
   * @param {string} [params.model] 模型名称
   * @param {Array<string>} params.options 分析选项 ['style', 'structure', 'keywords', 'sentiment']
   * @param {Function} [onProgress] 进度回调函数
   * @returns {Promise<Object>} 分析结果
   */
  async analyzeText(params, onProgress) {
    try {
      const response = await api.post('/analyze', params, {
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(percentCompleted);
          }
        }
      });
      return response.data;
    } catch (error) {
      console.error('文本分析失败:', error);
      throw error;
    }
  },

  /**
   * 获取支持的API提供商列表
   * @returns {Promise<Array<string>>} 提供商列表
   */
  async getProviders() {
    try {
      const response = await api.get('/api/providers');
      return response.data;
    } catch (error) {
      console.error('获取API提供商列表失败:', error);
      throw error;
    }
  },

  /**
   * 获取指定提供商支持的模型列表
   * @param {string} provider 提供商名称
   * @returns {Promise<Array<string>>} 模型列表
   */
  async getModels(provider) {
    try {
      const response = await api.get(`/api/providers/${provider}/models`);
      return response.data;
    } catch (error) {
      console.error('获取模型列表失败:', error);
      throw error;
    }
  }
};