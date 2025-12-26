<template>
  <div class="language-switcher">
    <el-dropdown @command="handleLanguageChange">
      <span class="language-switcher-link">
        {{ currentLocaleName }}
        <el-icon class="el-icon--right">
          <arrow-down />
        </el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item v-for="locale in availableLocales" 
                           :key="locale.value" 
                           :command="locale.value"
                           :class="{ 'is-active': locale.value === currentLocale }">
            {{ locale.label }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { setLocale, getCurrentLocale, getAvailableLocales } from '../../i18n'
import { ElMessage } from 'element-plus'

// 可用的语言列表
const locales = [
  { value: 'zh-CN', label: '中文' },
  { value: 'en-US', label: 'English' }
]

// 当前语言
const currentLocale = ref(getCurrentLocale())

// 当前语言的显示名称
const currentLocaleName = computed(() => {
  const locale = locales.find(item => item.value === currentLocale.value)
  return locale ? locale.label : '中文'
})

// 可用的语言列表
const availableLocales = computed(() => {
  return locales.filter(locale => getAvailableLocales().includes(locale.value))
})

// 切换语言
const handleLanguageChange = (locale) => {
  if (currentLocale.value !== locale) {
    const result = setLocale(locale)
    if (result) {
      currentLocale.value = locale
      ElMessage.success('语言切换成功')
      setTimeout(() => {
        window.location.reload() // 刷新页面以确保所有组件都重新渲染
      }, 500)
    }
  }
}

// 组件挂载时设置html的lang属性
onMounted(() => {
  document.querySelector('html').setAttribute('lang', currentLocale.value)
})
</script>

<style scoped lang="scss">
.language-switcher {
  display: inline-flex;
  align-items: center;
  cursor: pointer;

  &-link {
    display: flex;
    align-items: center;
    font-size: 14px;
    color: var(--el-text-color-primary);
    
    &:hover {
      color: var(--el-color-primary);
    }
  }
}

:deep(.el-dropdown-menu__item.is-active) {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}
</style> 