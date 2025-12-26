<template>
  <div class="guide-container">
    <el-alert
      title="操作指南"
      type="info"
      :closable="false"
      show-icon
    >
      <div class="tips-content">
        <p>• 调整参数后点击右上角的"保存参数"按钮即可应用设置</p>
        <p>• 对话中的参数调整会立即生效，无需重启</p>
        <p>• 可以点击"重置"恢复到模型默认值</p>
      </div>
    </el-alert>
  </div>
</template>

<script setup>
// 组件不需要参数，仅显示固定内容
</script>

<style scoped>
.guide-container {
  margin-bottom: 16px;
}

.tips-content {
  padding: 6px 0;
  line-height: 1.6;
}
</style> 