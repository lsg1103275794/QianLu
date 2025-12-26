<template>
  <div v-if="isLoading" class="loading-state">
    <el-icon class="is-loading"><Loading /></el-icon>
    <p>{{ addEmoji('正在努力生成研报，请稍候...', 'menu', 'loading') }}</p>
  </div>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue';
import { addEmoji } from '@/assets/emojiMap';

defineProps({
  isLoading: { type: Boolean, default: false }
});
</script>

<style scoped>
.loading-state {
  margin-top: 20px;
  padding: 15px;
  text-align: center;
  color: var(--el-text-color-secondary); /* Use Element Plus variable */
  border-radius: 4px;
}

.loading-state .el-icon {
  font-size: 28px;
  margin-bottom: 10px;
}
</style> 