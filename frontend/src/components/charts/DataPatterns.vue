<!-- DataPatterns.vue - 数据模式分析可视化组件 -->
<template>
  <div class="data-patterns">
    <el-card class="analysis-card">
      <template #header>
        <div class="gm-card-header">
          <div class="left-section">
            <h2 class="feature-title">{{ addEmoji('数据模式分析', 'menu', 'patterns') }}</h2>
            <el-tooltip content="分析文本中的数据模式和趋势" placement="top">
              <el-icon><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
        </div>
      </template>

      <!-- 文本输入区域 -->
      <el-form class="patterns-form" label-position="top">
        <el-form-item label="输入文本">
          <div class="gm-textarea-container">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="8"
              placeholder="请输入要分析的文本内容..."
              resize="none"
              class="gm-textarea"
            />
          </div>
          <div class="text-utils">
            <span class="char-count">{{ charCount }} 字符</span>
            <div class="text-actions">
              <el-button size="small" @click="clearText">清空</el-button>
              <el-button size="small" @click="pasteFromClipboard">粘贴</el-button>
            </div>
          </div>
        </el-form-item>

        <!-- 分析选项 -->
        <el-form-item label="分析选项">
          <div class="analysis-options">
            <el-checkbox v-model="options.numbers">{{ addEmoji('数字模式', 'feature', 'numbers') }}</el-checkbox>
            <el-checkbox v-model="options.dates">{{ addEmoji('日期模式', 'feature', 'dates') }}</el-checkbox>
            <el-checkbox v-model="options.keywords">{{ addEmoji('关键词频率', 'feature', 'frequency') }}</el-checkbox>
            <el-checkbox v-model="options.sentiment">{{ addEmoji('情感分析', 'feature', 'sentiment') }}</el-checkbox>
          </div>
        </el-form-item>

        <!-- 高级选项 -->
        <el-collapse class="advanced-options">
          <el-collapse-item title="高级选项" name="1">
            <el-form-item label="关键词筛选">
              <el-input
                v-model="keywordFilter"
                placeholder="输入关键词,用逗号分隔"
                :disabled="!options.keywords"
              />
            </el-form-item>
            <el-form-item label="情感分析粒度">
              <el-select
                v-model="sentimentGranularity"
                placeholder="选择粒度"
                :disabled="!options.sentiment"
                style="width: 100%;"
              >
                <el-option label="句子级别" value="sentence" />
                <el-option label="段落级别" value="paragraph" />
                <el-option label="整体" value="document" />
              </el-select>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>

        <!-- 操作按钮 -->
        <div class="form-action-buttons">
          <el-button 
            type="primary" 
            @click="analyzeData" 
            :disabled="!canAnalyze" 
            :loading="isAnalyzing"
            class="action-button"
          >
            <el-icon class="el-icon--left"><DataAnalysis /></el-icon>
            分析数据
          </el-button>
          <el-button @click="resetForm">
            <el-icon class="el-icon--left"><RefreshRight /></el-icon>
            重置
          </el-button>
        </div>
      </el-form>

      <!-- 分析结果区域 -->
      <div class="analysis-results" v-if="hasResults">
        <!-- 数值模式结果 -->
        <el-card class="result-card" v-if="options.numbers && results.numbers">
          <template #header>
            <div class="gm-card-header">
              <div class="left-section">
                <h3 class="section-title">{{ addEmoji('数值模式', 'feature', 'numbers') }}</h3>
              </div>
              <div class="right-section">
                <el-button size="small" @click="exportData('numbers')">
                  <el-icon class="el-icon--left"><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          <div class="numbers-results">
            <div class="stats-container">
              <div class="stat-item">
                <div class="stat-value">{{ results.numbers.count }}</div>
                <div class="stat-label">数值总数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.numbers.average.toFixed(2) }}</div>
                <div class="stat-label">平均值</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.numbers.median }}</div>
                <div class="stat-label">中位数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.numbers.min }}</div>
                <div class="stat-label">最小值</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.numbers.max }}</div>
                <div class="stat-label">最大值</div>
              </div>
            </div>
            <div class="chart-container" ref="numbersChartRef"></div>
          </div>
        </el-card>

        <!-- 日期模式结果 -->
        <el-card class="result-card" v-if="options.dates && results.dates">
          <template #header>
            <div class="gm-card-header">
              <div class="left-section">
                <h3 class="section-title">{{ addEmoji('日期模式', 'feature', 'dates') }}</h3>
              </div>
              <div class="right-section">
                <el-button size="small" @click="exportData('dates')">
                  <el-icon class="el-icon--left"><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          <div class="dates-results">
            <div class="stats-container">
              <div class="stat-item">
                <div class="stat-value">{{ results.dates.count }}</div>
                <div class="stat-label">日期总数</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.dates.dateRange }}</div>
                <div class="stat-label">日期范围</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.dates.mostFrequentDay }}</div>
                <div class="stat-label">最频繁日期</div>
              </div>
            </div>
            <div class="chart-container" ref="datesChartRef"></div>
          </div>
        </el-card>

        <!-- 关键词频率结果 -->
        <el-card class="result-card" v-if="options.keywords && results.keywords">
          <template #header>
            <div class="gm-card-header">
              <div class="left-section">
                <h3 class="section-title">{{ addEmoji('关键词频率', 'feature', 'frequency') }}</h3>
              </div>
              <div class="right-section">
                <el-button size="small" @click="exportData('keywords')">
                  <el-icon class="el-icon--left"><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          <div class="keywords-results">
            <div class="chart-container" ref="keywordsChartRef"></div>
            <el-table :data="results.keywords.topKeywords" style="width: 100%" height="250">
              <el-table-column prop="keyword" label="关键词" />
              <el-table-column prop="frequency" label="频率" sortable />
              <el-table-column prop="percentage" label="百分比" sortable>
                <template #default="scope">
                  {{ (scope.row.percentage * 100).toFixed(2) }}%
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <!-- 情感分析结果 -->
        <el-card class="result-card" v-if="options.sentiment && results.sentiment">
          <template #header>
            <div class="gm-card-header">
              <div class="left-section">
                <h3 class="section-title">{{ addEmoji('情感分析', 'feature', 'sentiment') }}</h3>
              </div>
              <div class="right-section">
                <el-button size="small" @click="exportData('sentiment')">
                  <el-icon class="el-icon--left"><Download /></el-icon>
                  导出
                </el-button>
              </div>
            </div>
          </template>
          <div class="sentiment-results">
            <div class="stats-container">
              <div class="stat-item sentiment-score">
                <div class="stat-value" :class="getSentimentClass(results.sentiment.overall)">
                  {{ results.sentiment.overall.toFixed(2) }}
                </div>
                <div class="stat-label">总体情感分</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.sentiment.positive.toFixed(2) }}</div>
                <div class="stat-label">积极度</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.sentiment.negative.toFixed(2) }}</div>
                <div class="stat-label">消极度</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ results.sentiment.neutral.toFixed(2) }}</div>
                <div class="stat-label">中性度</div>
              </div>
            </div>
            <div class="chart-container" ref="sentimentChartRef"></div>
          </div>
        </el-card>
      </div>

      <!-- 加载状态 -->
      <div class="gm-loading-container" v-if="isAnalyzing">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在分析数据...</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, DataAnalysis, Download, RefreshRight, Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts/core'
import { addEmoji } from '../../assets/emojiMap.js'
// ... 其他引入不变 ...
</script> 