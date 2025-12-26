<template>
  <el-dialog v-model="dialogVisible" title="聊天记录历史" width="80%" :top="'5vh'">
    <div v-loading="loading" style="max-height: 70vh; overflow-y: auto;">
      <div v-if="!chatLogs || chatLogs.length === 0" class="empty-logs">
        <el-empty description="暂无聊天记录" />
      </div>
      <el-table v-else :data="chatLogs" style="width: 100%" @row-click="handleRowClick" :row-class-name="tableRowClassName">
        <el-table-column prop="provider" label="服务商" width="120">
          <template #default="scope">
            <el-tag size="small" type="info">{{ scope.row.provider }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型" width="200" show-overflow-tooltip />
        <el-table-column prop="first_user_message" label="首条消息">
          <template #default="scope">
            <div class="message-preview">{{ scope.row.first_user_message || '(无内容)' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="messages_count" label="消息数" width="80" align="center">
          <template #default="scope">
            <el-badge :value="scope.row.messages_count" type="info" />
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="时间" width="170">
          <template #default="scope">
            {{ formatDate(scope.row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" @click.stop="$emit('load-detail', scope.row.id)">
              加载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="dialogVisible = false">关闭</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  chatLogs: { type: Array, default: () => [] }
});

const emit = defineEmits(['update:modelValue', 'load-detail']);

// 双向绑定
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
});

const handleRowClick = (row) => {
  emit('load-detail', row.id);
};

// 格式化日期
const formatDate = (timestamp) => {
  if (!timestamp) return '未知时间';
  const date = new Date(timestamp);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  
  // 格式化时间部分
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const timeStr = `${hours}:${minutes}`;
  
  // 当天显示时间，昨天显示"昨天"，前天显示"前天"，其他显示日期
  if (diffDays === 0) {
    return `今天 ${timeStr}`;
  } else if (diffDays === 1) {
    return `昨天 ${timeStr}`;
  } else if (diffDays === 2) {
    return `前天 ${timeStr}`;
  } else {
    return `${date.getMonth() + 1}月${date.getDate()}日 ${timeStr}`;
  }
};

// 定义表格行的类名
// eslint-disable-next-line no-unused-vars
const tableRowClassName = ({ row, rowIndex }) => {
  return 'chat-history-row';
};
</script>

<style lang="scss" scoped>
.empty-logs {
  padding: 40px 0;
  text-align: center;
}

.message-preview {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

:deep(.chat-history-row) {
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: var(--el-fill-color-light) !important;
  }
  
  td {
    padding: 10px 0;
  }
}

.el-dialog :deep(.el-dialog__body) {
  padding-top: 10px;
  padding-bottom: 10px;
}
</style>
