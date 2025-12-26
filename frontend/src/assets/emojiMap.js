/**
 * UI元素Emoji映射系统
 * 这个文件集中管理所有UI元素的emoji映射，让应用界面更丰富有趣
 */

// 导航菜单项映射
export const MENU_EMOJI = {
  // 主要导航菜单
  'text-analysis': '📊',
  'writing-style-analysis': '📝',
  'excel-analysis': '📈',
  'style-transfer': '🎭',
  'api-manager': '🔌',
  'model-test': '🤖',
  'chat': '💬',
  'settings': '⚙️',
  'data-terminal': '🧮',
  'dashboard': '📋',
  'documents': '📑',
  'analytics': '📈',
  'profile': '👤',
  'admin': '👑',
  'help': '❓',
  'about': 'ℹ️',
  
  // 通用UI元素
  'home': '🏠',
  'back': '◀️',
  'forward': '▶️',
  'save': '💾',
  'upload': '📤',
  'download': '📥',
  'copy': '📋',
  'delete': '🗑️',
  'edit': '✏️',
  'refresh': '🔄',
  'search': '🔍',
  'confirm': '✔️',
  'cancel': '✖️',
  'expand': '➕',
  'collapse': '➖',
  'theme': '🎨',
  'add': '➕',
  'remove': '➖',
  'clear': '🧹',
  'preview': '👁️',
  'view': '👓',
  'share': '🔄',
  'export': '📤',
  'import': '📥',
  'run': '▶️',
  'pause': '⏸️',
  'stop': '⏹️',
  'reset': '🔄',
  'result': '📝',
  'list': '📋',
  'grid': '🔲',
  'table': '🏓',
  'chart': '📊',
  'compare': '⚖️',
  'history': '🕒',
  
  // 状态与通知
  'success': '✅',
  'error': '❌',
  'warning': '⚠️',
  'info': '📝',
  'loading': '⏳',
  'in-progress': '🔄',
  'completed': '✅',
  'pending': '⏱️',
  'approved': '👍',
  'rejected': '👎',
  'notification': '🔔',
  'alert': '🚨',
  
  // 主题设置
  'dark-mode': '🌙',
  'light-mode': '☀️',
  'auto-mode': '🌓',
  'custom-theme': '🎨',
  
  // 特殊功能
  'settings-advanced': '🛠️',
  'favourite': '⭐',
  'language': '🌐',
  'template': '📄',
  'select-template': '📋',
  'template-list': '📑',
  'debug': '🐞',
  'test-connection': '🔗',
  'user-profile': '👤',
  'account': '🔑',
  'logout': '🚪',
  'login': '🔐',
  'register': '📝',
  'bookmark': '🔖',
  'statistics': '📊',
  'report-generator': '🧾',
  'feedback': '📢',
  'support': '🙋',
  'update': '🔄',
  'version': '🏷️',
  'config': '⚙️',
  'install': '💽',
  'uninstall': '🗑️',
  'cloud': '☁️',
  'local': '💻',
  'sync': '🔄',
  'backup': '📦',
  'restore': '🔙',
  'secure': '🔒',
  'unlock': '🔓',
  
  // 补充按钮/操作类Emoji
  'submit': '✅',       // 提交
  'start': '▶️',        // 开始
  'generate': '✨',     // 生成 (借用feature的)
  'analyze': '🔬',      // 分析 (借用feature的)
  'next': '➡️',         // 下一步
  'previous': '⬅️',      // 上一步
  'finish': '🏁',       // 完成
  'ok': '👌',           // 好的
  'apply': '👍',        // 应用
  'details': 'ℹ️',       // 详情
  'more': '➕',         // 更多 (展开)
  'less': '➖',         // 更少 (收起)
  'options': '🔧',       // 选项
  'configure': '⚙️',    // 配置 (同 settings)
  'connect': '🔗',       // 连接
  'disconnect': '🚫',   // 断开
  'send': '✉️',         // 发送
  'retry': '🔄',        // 重试 (同 refresh)
  'sort': '↕️',         // 排序
  'filter': '⚖️'        // 筛选 (更新一个更形象的, 原有 filter 像 search)
};

// API提供商映射
export const PROVIDER_EMOJI = {
  'ollama_local': '🦙',
  'volc_engine': '🌋',
  'silicon_flow': '🌊',
  'zhipu_ai': '🧠',
  'deepseek_ai': '🔍',
  'google_gemini': '✨',
  'openai': '💡',
  'azure': '☁️',
  'anthropic': '🤔',
  'qwen': '🧩',
  'mistral': '🌀',
  'claude': '🧠',
  'baidu': '🐼',
  'minimax': '🔮',
  'xunfei': '🎤',
  'groq_api': '⚡',
  'together_ai': '🤝',
  'perplexity_ai': '🧩',
  'anyscale_endpoints': '📡',
  'cohere_compatible': '🔄',
  'open_router': '🛣️',
  'stability_ai': '🖼️',
  'replicate': '🔁',
  'local_ai': '🏠',
  'hugging_face': '🤗',
  'chatglm': '💬',
  
  // 通用类型
  'default': '⚡',
  'unknown': '❓'
};

// 功能维度映射
export const FEATURE_EMOJI = {
  // 文本分析维度
  'sentiment': '😊',
  'readability': '📖',
  'style': '✨',
  'structure': '🏗️',
  'tone': '🎵',
  'vocabulary': '📚',
  'text_stats': '🧮',
  'word_freq': '📶',
  'sentence_structure': '¶',
  'keyword_extraction': '🔑',
  'language_features': '🔡',
  'grammar': '📏',
  'coherence': '🔄',
  'clarity': '🔍',
  'emotion': '🎭',
  'objectivity': '⚖️',
  'persuasiveness': '🎯',
  
  // 风格迁移相关
  'style-transfer': '🎭',
  'content-transfer': '🔄',
  'theme-change': '🎯',
  'tone-transfer': '🎵',
  'rewrite': '✍️',
  'paraphrase': '📝',
  'text-generation': '📢',
  'creative-writing': '💫',
  'storytelling': '📚',
  'educational': '🎓',
  'technical': '⚙️',
  'poetic': '🌈',
  'formal': '👔',
  'casual': '👕',
  'humorous': '😄',
  'serious': '🧐',
  
  // 新增本地分析维度
  'stats': '📊',
  'frequency': '📈',
  'pattern': '🔣',
  'keywords': '🔑',
  'language': '🔤',
  
  // 模型参数
  'temperature': '🌡️',
  'max_tokens': '📏',
  'top_p': '🔝',
  'top_k': '🔢',
  'frequency_penalty': '📉',
  'presence_penalty': '🚫',
  'stop_sequence': '⛔',
  'sampling': '🎲',
  
  // 聊天相关
  'user': '👤',
  'assistant': '🤖',
  'system': '🖥️',
  'history': '📜',
  'chat_log': '💬',
  'message': '✉️',
  'conversation': '🗣️',
  'thread': '🧵',
  'feedback': '📨',
  
  // API状态
  'api_configured': '✅',
  'api_not_configured': '❌',
  'api_error': '⚠️',
  'api_success': '🟢',
  'api_warning': '🟠',
  'api_info': '🔵',

  // 新增：状态指示灯
  'status-ok': '🟢',
  'status-warning': '🟠',
  'status-error': '🔴',
  'status-pending': '⚪',
  'progress': '📈',
  'complete': '✅',
  'loading': '⏳',
  'waiting': '⌛',
  'service_status': '🔌',

  // 新增：文件类型
  'file-pdf': '📄',
  'file-doc': '📃',
  'file-txt': '📝',
  'file-generic': '📎',
  'file-image': '🖼️',
  'file-audio': '🔊',
  'file-video': '🎬',
  'file-code': '📋',
  'file-data': '📊',
  'file-archive': '🗄️',
  
  // 新增：用户界面元素
  'ui-button': '🔘',
  'ui-dropdown': '📋',
  'ui-slider': '🎚️',
  'ui-toggle': '🔄',
  'ui-checkbox': '✅',
  'ui-radio': '⭕',
  'ui-input': '📝',
  'ui-output': '📤',
  'ui-card': '🗂️',
  'ui-dialog': '💭',
  
  // 新增：功能分类
  'function-analyze': '🔬',
  'function-generate': '✨',
  'function-transform': '🔄',
  'function-compare': '⚖️',
  'function-extract': '🔍',
  'function-classify': '📋',
  'function-summarize': '📝',
  'function-translate': '🌐'
};

// 获取特定类型的emoji
export function getEmoji(type, key, fallback = '') {
  let map;
  
  switch(type) {
    case 'menu':
      map = MENU_EMOJI;
      break;
    case 'provider':
      map = PROVIDER_EMOJI;
      break;
    case 'feature':
      map = FEATURE_EMOJI;
      break;
    default:
      return fallback;
  }
  
  return map[key] || fallback;
}

// 为文本添加emoji前缀
export function addEmoji(text, type, key) {
  const emoji = getEmoji(type, key, '');
  return emoji ? `${emoji} ${text}` : text;
}