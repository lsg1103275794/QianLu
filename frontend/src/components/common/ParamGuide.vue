<template>
  <div class="param-guide-container">
    <el-alert
      title="参数影响指南"
      type="success"
      :closable="false"
      show-icon
    >
      <div class="tips-content">
        <p>• <b>温度</b>: 值越高，回复越多样化但可能偏离主题；值越低，回复越精确但可能重复</p>
        <p>• <b>最大长度</b>: 控制输出的最大Token数，合理设置以避免过长或截断</p>
        <p>• <b>Top P</b>: 控制词汇选择的范围，值越高创造性越强；值越低，精确性越高</p>
      </div>
    </el-alert>
  </div>
</template>

<script setup>
// 组件不需要参数，仅显示固定内容
</script>

<style scoped>
.param-guide-container {
  margin-bottom: 16px;
}

.tips-content {
  padding: 6px 0;
  line-height: 1.6;
}
</style> 