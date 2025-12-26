<template>
  <transition name="fade">
    <div v-if="progress > 0" class="loading-progress-container">
      <div class="loading-info">
        <span class="loading-text">{{ message || '加载中...' }}</span>
        <span class="loading-percentage">{{ Math.round(progress) }}%</span>
      </div>
      <el-progress 
        :percentage="progress" 
        :stroke-width="3" 
        :show-text="false"
        status="success"
      ></el-progress>
    </div>
  </transition>
</template>

<script setup>
defineProps({
  progress: { type: Number, default: 0 },
  message: { type: String, default: '加载中...' }
});
</script>

<style lang="scss" scoped>
.loading-progress-container {
  padding: 8px 16px;
  background: linear-gradient(to bottom, rgba(var(--el-color-primary-rgb), 0.1), transparent);
  z-index: 100;
  flex-shrink: 0;
}

.loading-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  font-size: 12px;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
