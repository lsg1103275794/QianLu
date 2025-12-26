import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

// 获取默认语言
const getDefaultLocale = () => {
  // 首先从本地存储中获取用户设置
  const savedLocale = localStorage.getItem('locale')
  if (savedLocale) {
    return savedLocale
  }
  
  // 获取浏览器首选语言
  const browserLang = navigator.language || navigator.userLanguage
  
  // 如果浏览器语言是中文，返回zh-CN，否则返回en-US
  return browserLang.startsWith('zh') ? 'zh-CN' : 'en-US'
}

// 创建i18n实例
const i18n = createI18n({
  legacy: false, // 启用 Composition API 模式
  locale: getDefaultLocale(),
  fallbackLocale: 'zh-CN', // 默认回退到中文
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  },
  silentTranslationWarn: true // 在生产环境中隐藏翻译警告
})

// 导出语言切换函数
export const setLocale = (locale) => {
  if (i18n.global.availableLocales.includes(locale)) {
    i18n.global.locale.value = locale
    localStorage.setItem('locale', locale)
    document.querySelector('html').setAttribute('lang', locale)
    return true
  }
  return false
}

// 获取当前的语言
export const getCurrentLocale = () => {
  return i18n.global.locale.value
}

// 获取可用的语言列表
export const getAvailableLocales = () => {
  return i18n.global.availableLocales
}

export default i18n 