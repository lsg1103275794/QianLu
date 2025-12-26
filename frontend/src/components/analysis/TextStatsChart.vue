<template>
  <div class="text-stats-chart">
    <div class="stats-panel">
      <div class="stats-section basic-stats">
        <h3>基本文本统计</h3>
        <div class="stats-grid">
          <div class="stat-card" v-for="(item, index) in basicStats" :key="index">
            <div class="stat-icon" :class="item.icon" :style="{ background: `${item.color}20`, color: item.color }"></div>
            <div class="stat-value" :style="{ color: item.color }">{{ formatValue(item.value) }}</div>
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-progress">
              <div class="progress-bar" :style="{
                width: getProgressWidth(item.value, item.max),
                background: `linear-gradient(to right, ${item.color}50, ${item.color})`
              }"></div>
            </div>
            <div class="stat-tooltip" v-if="item.tooltip">{{ item.tooltip }}</div>
          </div>
        </div>
      </div>

      <div class="stats-section advanced-stats">
        <h3>高级文本统计</h3>
        <div class="stats-grid">
          <div class="stat-card" v-for="(item, index) in advancedStats" :key="index">
            <div class="stat-icon" :class="item.icon" :style="{ background: `${item.color}20`, color: item.color }"></div>
            <div class="stat-value" :style="{ color: item.color }">{{ formatValue(item.value) }}{{ item.suffix || '' }}</div>
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-indicator" v-if="item.indicator">
              <span class="indicator-dot" :class="item.indicator"></span>
              <span class="indicator-text">{{ getIndicatorText(item.indicator) }}</span>
            </div>
            <div class="stat-tooltip" v-if="item.tooltip">{{ item.tooltip }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="chart-section" v-if="hasCharDistribution">
      <h3>字符分布</h3>
      <div ref="charDistributionChart" class="distribution-chart"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  text_stats: {
    type: Object,
    required: true
  }
})

const charDistributionChart = ref(null)
let chartInstance = null

const basicStats = computed(() => {
  const stats = props.text_stats || {}
  // 适配不同的数据结构
  let data = {}
  
  // 如果有basic属性，则使用basic中的数据
  if (stats.basic) {
    data = stats.basic
  } else {
    // 否则尝试从顶层获取数据
    data = stats
  }
  
  return [
    {
      label: '字符总数',
      value: data.char_count || data.charCount || 0,
      icon: 'icon-char',
      max: 50000,
      color: getStatColor(data.char_count || data.charCount || 0, 3000, 10000, 30000),
      tooltip: getCharCountTip(data.char_count || data.charCount || 0)
    },
    {
      label: '中文字数',
      value: data.chinese_char_count || data.chineseCharCount || 0,
      icon: 'icon-zh',
      max: 30000,
      color: getStatColor(data.chinese_char_count || data.chineseCharCount || 0, 2000, 8000, 20000),
      tooltip: getChineseCountTip(data.chinese_char_count || data.chineseCharCount || 0)
    },
    {
      label: '词数',
      value: data.word_count || data.wordCount || 0,
      icon: 'icon-word',
      max: 25000,
      color: getStatColor(data.word_count || data.wordCount || 0, 1500, 5000, 15000),
      tooltip: getWordCountTip(data.word_count || data.wordCount || 0)
    },
    {
      label: '句子数',
      value: data.sentence_count || data.sentenceCount || 0,
      icon: 'icon-sentence',
      max: 1000,
      color: getStatColor(data.sentence_count || data.sentenceCount || 0, 100, 300, 600),
      tooltip: getSentenceCountTip(data.sentence_count || data.sentenceCount || 0)
    },
    {
      label: '段落数',
      value: data.paragraph_count || data.paragraphCount || 0,
      icon: 'icon-paragraph',
      max: 100,
      color: getStatColor(data.paragraph_count || data.paragraphCount || 0, 10, 30, 60),
      tooltip: getParagraphCountTip(data.paragraph_count || data.paragraphCount || 0)
    }
  ]
})

const advancedStats = computed(() => {
  const stats = props.text_stats || {}
  // 适配不同的数据结构
  let data = {}
  
  // 如果有advanced属性，则使用advanced中的数据
  if (stats.advanced) {
    data = stats.advanced
  } else {
    // 否则尝试从顶层获取数据
    data = stats
  }
  
  const avgSentenceLength = data.avg_sentence_length || data.avgSentenceLength || 0
  const avgParagraphLength = data.avg_paragraph_length || data.avgParagraphLength || 0
  const readingTime = data.reading_time || data.readingTimeMin || 0
  
  return [
    {
      label: '平均句长',
      value: avgSentenceLength,
      icon: 'icon-avg-length',
      indicator: getComplexityIndicator(avgSentenceLength, 15, 25, 35),
      color: getSentenceLengthColor(avgSentenceLength),
      tooltip: getSentenceLengthTip(avgSentenceLength)
    },
    {
      label: '平均段落长度',
      value: avgParagraphLength,
      icon: 'icon-paragraph-length',
      indicator: getComplexityIndicator(avgParagraphLength, 3, 5, 8),
      color: getParagraphLengthColor(avgParagraphLength),
      tooltip: getParagraphLengthTip(avgParagraphLength)
    },
    {
      label: '预计阅读时间',
      value: readingTime,
      icon: 'icon-time',
      suffix: '分钟',
      color: getReadingTimeColor(readingTime),
      tooltip: getReadingTimeTip(readingTime)
    }
  ]
})

const hasCharDistribution = computed(() => {
  const stats = props.text_stats || {}
  return (stats.char_distribution || stats.charDistribution || (stats.basic && stats.basic.char_distribution) || (stats.basic && stats.basic.charDistribution))
})

const formatValue = (value) => {
  if (value === undefined || value === null) return '0'
  if (typeof value === 'number') {
    return value % 1 === 0 ? value.toString() : value.toFixed(1)
  }
  if (typeof value === 'string' && value.includes('min')) {
    return value.replace('min', '分钟')
  }
  return value
}

const getProgressWidth = (value, max) => {
  if (!value || !max) return '0%'
  const percentage = Math.min(100, (value / max) * 100)
  return `${percentage}%`
}

const getComplexityIndicator = (value, low, medium, high) => {
  if (value === undefined || value === null) return null
  if (value < low) return 'simple'
  if (value < medium) return 'moderate'
  if (value < high) return 'complex'
  return 'very-complex'
}

const getIndicatorText = (indicator) => {
  const map = {
    'simple': '简单',
    'moderate': '适中',
    'complex': '复杂',
    'very-complex': '非常复杂'
  }
  return map[indicator] || ''
}

const getStatColor = (value, low, medium, high) => {
  if (value < low) return 'var(--el-color-info)'
  if (value < medium) return 'var(--el-color-primary)'
  if (value < high) return 'var(--el-color-warning)'
  return 'var(--el-color-danger)'
}

const getSentenceLengthColor = (value) => {
  if (value < 15) return 'var(--el-color-success)' // 短句，易读
  if (value < 25) return 'var(--el-color-primary)' // 中等，正常
  if (value < 35) return 'var(--el-color-warning)' // 较长，有些复杂
  return 'var(--el-color-danger)' // 非常长，难读
}

const getParagraphLengthColor = (value) => {
  if (value < 3) return 'var(--el-color-success)' // 短段落，易读
  if (value < 5) return 'var(--el-color-primary)' // 中等
  if (value < 8) return 'var(--el-color-warning)' // 较长
  return 'var(--el-color-danger)' // 非常长，可能过于复杂
}

const getReadingTimeColor = (value) => {
  if (value < 5) return 'var(--el-color-success)' // 短文，快速阅读
  if (value < 15) return 'var(--el-color-primary)' // 中等长度
  if (value < 30) return 'var(--el-color-warning)' // 较长
  return 'var(--el-color-danger)' // 非常长，需要较长时间
}

const getCharCountTip = (value) => {
  if (value < 3000) return '短文本，适合快速阅读'
  if (value < 10000) return '中等长度文本'
  if (value < 30000) return '较长文本，内容丰富'
  return '长篇文本，内容充实'
}

const getChineseCountTip = (value) => {
  if (value < 2000) return '短文本，适合快速阅读'
  if (value < 8000) return '中等长度中文文本'
  if (value < 20000) return '较长中文文本，内容丰富'
  return '长篇中文文本，内容充实'
}

const getWordCountTip = (value) => {
  if (value < 1500) return '短文本，适合快速阅读'
  if (value < 5000) return '中等长度，约等于10-15页文章'
  if (value < 15000) return '较长文本，类似小论文长度'
  return '长篇文本，接近小册子长度'
}

const getSentenceCountTip = (value) => {
  if (value < 100) return '短文本，段落少'
  if (value < 300) return '中等长度，结构适中'
  if (value < 600) return '较长文本，结构较复杂'
  return '长篇文本，结构复杂'
}

const getParagraphCountTip = (value) => {
  if (value < 10) return '短文本，段落少'
  if (value < 30) return '中等长度，结构适中'
  if (value < 60) return '较长文本，结构丰富'
  return '长篇文本，段落丰富'
}

const getSentenceLengthTip = (value) => {
  if (value < 15) return '句子简短，易于理解'
  if (value < 25) return '句子长度适中，阅读流畅'
  if (value < 35) return '句子较长，可能需要更多注意力'
  return '句子非常长，可能难以理解'
}

const getParagraphLengthTip = (value) => {
  if (value < 3) return '段落简短，阅读轻松'
  if (value < 5) return '段落长度适中，结构清晰'
  if (value < 8) return '段落较长，信息较丰富'
  return '段落非常长，信息密集'
}

const getReadingTimeTip = (value) => {
  if (value < 5) return '可在短暂休息时阅读完毕'
  if (value < 15) return '适合通勤期间阅读'
  if (value < 30) return '需要预留一定时间阅读'
  return '建议分多次阅读完成'
}

const initCharDistributionChart = () => {
  if (!charDistributionChart.value) return
  
  const stats = props.text_stats || {}
  const distribution = stats.char_distribution || stats.charDistribution || 
                       (stats.basic && stats.basic.char_distribution) || 
                       (stats.basic && stats.basic.charDistribution)
                       
  if (!distribution) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(charDistributionChart.value)
  
  let data = []
  
  // 处理常见字符类型
  const typeMapping = {
    'chinese': '中文字符',
    'letters': '英文字母',
    'digits': '数字',
    'punctuations': '标点符号',
    'spaces': '空格',
    'others': '其他字符'
  }
  
  // 尝试不同的数据结构格式
  if (typeof distribution === 'object' && !Array.isArray(distribution)) {
    // 处理对象格式的数据
    Object.entries(distribution).forEach(([key, value]) => {
      const name = typeMapping[key.toLowerCase()] || key
      let dataValue = value
      
      // 处理可能的数据格式: { percent: xx } 或 { count: xx }
      if (typeof value === 'object' && value !== null) {
        dataValue = value.percent !== undefined ? value.percent : (value.count || 0)
      }
      
      if (dataValue > 0) {
        data.push({ name, value: dataValue })
      }
    })
  } else if (Array.isArray(distribution)) {
    // 处理数组格式的数据
    data = distribution.map(item => ({
      name: item.name || item.type || '未知',
      value: item.value || item.percent || item.count || 0
    }))
  }
  
  // 数据排序和截取
  data = data
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 10) // 只显示前10种字符类型
  
  // 确保数据非空
  if (data.length === 0) {
    data = [
      { name: '暂无数据', value: 100 }
    ]
  }
  
  const colors = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666',
    '#73c0de', '#3ba272', '#fc8452', '#9a60b4',
    '#ea7ccc', '#6e7079'
  ]
  
  const option = {
    color: colors,
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      type: 'scroll',
      textStyle: {
        color: 'var(--el-text-color-primary)'
      }
    },
    series: [
      {
        name: '字符分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: 'var(--el-bg-color)',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '14',
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        labelLine: {
          show: false
        },
        data: data,
        animationType: 'scale',
        animationEasing: 'elasticOut',
        // eslint-disable-next-line no-unused-vars
        animationDelay: function (_idx) {
          return Math.random() * 200
        }
      }
    ]
  }
  
  chartInstance.setOption(option)
}

const initCharts = () => {
  setTimeout(() => {
    if (document.visibilityState === 'visible') {
      try {
        initCharDistributionChart()
      } catch (error) {
        console.error('Error initializing charts:', error)
      }
    }
  }, 50)
}

watch(() => props.text_stats, () => {
  initCharts()
}, { deep: true })

onMounted(() => {
  initCharts()
  window.addEventListener('resize', initCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', initCharts)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.text-stats-chart {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 16px 0;
}

.stats-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
  gap: 24px;
}

.stats-section {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

h3 {
  font-size: 16px;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-light);
  color: var(--el-text-color-primary);
  position: relative;
}

h3:after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 60px;
  height: 3px;
  background: var(--el-color-primary);
  border-radius: 2px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}

.stat-card {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.stat-card:hover .stat-tooltip {
  opacity: 1;
  transform: translateY(0);
}

.stat-icon {
  width: 40px;
  height: 40px;
  background: var(--el-color-primary-light-8);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  font-size: 20px;
  color: var(--el-color-primary);
  transition: all 0.3s;
}

.stat-card:hover .stat-icon {
  background: var(--el-color-primary-light-5);
  transform: scale(1.1);
}

.icon-char:after { content: 'Aa'; font-weight: bold; }
.icon-zh:after { content: '中'; font-weight: bold; }
.icon-word:after { content: '词'; }
.icon-sentence:after { content: '句'; }
.icon-paragraph:after { content: '段'; }
.icon-avg-length:after { content: '长'; }
.icon-paragraph-length:after { content: '段长'; font-size: 14px; }
.icon-time:after { content: '⏱'; }

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 10px;
}

.stat-progress {
  height: 4px;
  width: 100%;
  background: var(--el-fill-color-darker);
  border-radius: 2px;
  overflow: hidden;
  margin-top: auto;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(to right, var(--el-color-primary-light-5), var(--el-color-primary));
  border-radius: 2px;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.simple {
  background-color: var(--el-color-success);
}

.moderate {
  background-color: var(--el-color-primary);
}

.complex {
  background-color: var(--el-color-warning);
}

.very-complex {
  background-color: var(--el-color-danger);
}

.indicator-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.chart-section {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.distribution-chart {
  height: 300px;
  width: 100%;
}

.stat-tooltip {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.75);
  color: white;
  padding: 6px 8px;
  font-size: 12px;
  border-radius: 0 0 8px 8px;
  opacity: 0;
  transform: translateY(100%);
  transition: all 0.3s;
  z-index: 10;
}

@media (max-width: 768px) {
  .stats-panel {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
  }

  .stat-card {
    padding: 12px 8px;
  }

  .stat-icon {
    width: 32px;
    height: 32px;
    font-size: 16px;
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 20px;
  }

  .stat-label {
    font-size: 12px;
  }

  .distribution-chart {
    height: 240px;
  }
}
</style> 