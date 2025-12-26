import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import router from './router'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
// import api from './services/api' // Removed unused import
import './assets/styles/global.scss'
import i18n from './i18n' // 导入i18n配置

// 导入echarts和echarts-wordcloud
import * as echarts from 'echarts'
import 'echarts-wordcloud'

const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.use(i18n) // 注册i18n

// 全局挂载echarts
app.config.globalProperties.$echarts = echarts

// 可选：将 api 实例挂载到全局属性，方便组件内调用
// app.config.globalProperties.$api = api;

// 添加全局错误处理，解决ResizeObserver错误
const originalConsoleError = console.error;
console.error = (...args) => {
  if (
    args.length > 0 &&
    typeof args[0] === 'string' &&
    args[0].includes('ResizeObserver') &&
    args[0].includes('loop')
  ) {
    // 忽略ResizeObserver循环错误
    return;
  }
  originalConsoleError.apply(console, args);
};

// 添加全局错误处理器
window.addEventListener('error', (event) => {
  if (
    event.message &&
    (event.message.includes('ResizeObserver') || 
     event.message.includes('ResizeObserver loop completed with undelivered notifications'))
  ) {
    event.stopPropagation();
    event.preventDefault();
    console.warn('全局错误处理器: 已忽略 ResizeObserver 错误');
    return false;
  }
}, true);

app.mount('#app') 