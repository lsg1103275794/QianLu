// Import functions from individual service modules
import * as utilsService from './utilsService';
import * as statusService from './statusService';
import * as providerService from './providerService';
import * as analysisService from './analysisService';
import * as styleService from './styleService';
import * as taskService from './taskService';
import * as settingsService from './settingsService';
import * as chatService from './chatService';
import * as fileService from './fileService';
import * as resultsService from './resultsService';
import * as uiStateService from './uiStateService';
import * as mockService from './mockService'; // Assuming mock functions might still be needed

// 直接导入streamChat
import { streamChat } from './chatService';

// Combine all functions into a single 'api' object
const api = {
  ...utilsService,
  ...statusService,
  ...providerService,
  ...analysisService,
  ...styleService,
  ...taskService,
  ...settingsService,
  ...chatService,
  ...fileService,
  ...resultsService,
  ...uiStateService,
  ...mockService,
  // 确保streamChat优先导出，覆盖可能的重复定义
  streamChat
};

// Export the combined object as the default export
export default api;