<template>
  <div v-if="errorText" class="error-display">
    <el-alert type="error" :closable="false" show-icon>
      <template #title>{{ addEmoji('生成出错', 'menu', 'error') }}</template>
      <pre>{{ errorText }}</pre>
    </el-alert>
  </div>
</template>

<script setup>
import { ElAlert } from 'element-plus';
import { addEmoji } from '@/assets/emojiMap';

defineProps({
  errorText: { type: String, default: '' }
});
</script>

<style scoped>
.error-display {
  margin-top: 20px;
}

.error-display pre {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: monospace;
  font-size: 0.9em;
  color: var(--el-color-error); /* Use Element Plus variable */
  background-color: var(--el-color-error-light-9); /* Use Element Plus variable */
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
}
</style> 