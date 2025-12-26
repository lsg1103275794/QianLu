<template>
  <div class="readability-chart">
    <div class="chart-container score-summary">
      <h3>可读性评分</h3>
      <div class="score-display">
        <div class="score-circle" :style="{ background: getScoreColor(readability.readabilityScore) }">
          {{ Math.round(readability.readabilityScore) }}
        </div>
        <div class="score-info">
          <div class="score-level">{{ readability.readabilityLevel || 'easy' }}</div>
          <div class="score-desc">{{ getScoreDescription(readability.readabilityScore) }}</div>
        </div>
      </div>
    </div>

    <div class="chart-container">
      <h3>阅读难度指数</h3>
      <div class="reading-scale">
        <div class="scale-container">
          <div class="scale-line"></div>
          <div class="scale-marker" 
               v-for="(mark, index) in scaleMarkers" 
               :key="index"
               :style="{ left: mark.position + '%' }">
            <div class="marker-dot" :style="{ background: mark.color }"></div>
            <div class="marker-label">{{ mark.label }}</div>
          </div>
          <div class="scale-pointer" :style="{ left: pointerPosition + '%' }">
            <div class="pointer-dot"></div>
            <div class="pointer-value">{{ Math.round(readability.readabilityScore) }}</div>
          </div>
        </div>
        <div class="scale-labels">
          <div>极易</div>
          <div>容易</div>
          <div>适中</div>
          <div>困难</div>
          <div>极难</div>
        </div>
      </div>
    </div>

    <div class="chart-container text-stats-container">
      <h3>文本统计</h3>
      <div class="stats-grid" v-if="readability.text_stats">
        <div v-for="(value, key) in formatTextStats(readability.text_stats)" :key="key" class="stat-item">
          <div class="stat-icon" :class="getStatIconClass(key)"></div>
          <div class="stat-label">{{ formatLabel(key) }}</div>
          <div class="stat-value">{{ formatValue(value) }}</div>
        </div>
      </div>
    </div>
    
    <div class="chart-container scores-container" v-if="readability.scores">
      <h3>专业可读性指标</h3>
      <div ref="scoreChartRef" class="chart"></div>
      <div class="scores-legend">
        <div class="legend-item" v-for="(desc, index) in scoreLegend" :key="index">
          <div class="legend-color" :style="{ background: getColorForScore(index * 20) }"></div>
          <div class="legend-text">{{ desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  readability: {
    type: Object,
    required: true
  }
})

const scoreChartRef = ref(null)
let scoreChart = null

const formatTextStats = (stats) => {
  if (!stats) return {}
  const result = {}
  
  if (stats.char_count !== undefined) result.char_count = stats.char_count
  if (stats.word_count !== undefined) result.word_count = stats.word_count
  if (stats.sentence_count !== undefined) result.sentence_count = stats.sentence_count
  if (stats.avg_sentence_length !== undefined) result.avg_sentence_length = stats.avg_sentence_length
  if (stats.reading_time !== undefined) result.reading_time = stats.reading_time
  
  return result
}

const getStatIconClass = (key) => {
  const iconMap = {
    char_count: 'icon-character',
    word_count: 'icon-word',
    sentence_count: 'icon-sentence',
    avg_sentence_length: 'icon-length',
    reading_time: 'icon-time'
  }
  return iconMap[key] || 'icon-default'
}

const formatLabel = (key) => {
  const labelMap = {
    char_count: '字符数',
    word_count: '词数',
    sentence_count: '句子数',
    avg_word_length: '平均词长',
    avg_sentence_length: '平均句长',
    complex_word_ratio: '复杂词比例',
    reading_time: '阅读时间',
    speaking_time: '朗读时间'
  }
  return labelMap[key] || key
}

const formatValue = (value) => {
  if (typeof value === 'number') {
    if (Number.isInteger(value)) {
      return value.toString()
    }
    return value.toFixed(1)
  }
  if (typeof value === 'string' && value.includes('min')) {
    return value.replace('min', '分钟')
  }
  return value
}

const getScoreColor = (score) => {
  if (score >= 90) return 'var(--el-color-success)'
  if (score >= 80) return 'var(--el-color-success-light)'
  if (score >= 70) return 'var(--el-color-warning-light)'
  if (score >= 60) return 'var(--el-color-warning)'
  if (score >= 50) return 'var(--el-color-danger-light)'
  return 'var(--el-color-danger)'
}

const getColorForScore = (score) => {
  if (score >= 90) return 'var(--el-color-success)'
  if (score >= 80) return 'var(--el-color-success-light)'
  if (score >= 70) return 'var(--el-color-warning-light)'
  if (score >= 60) return 'var(--el-color-warning)'
  if (score >= 50) return 'var(--el-color-danger-light)'
  return 'var(--el-color-danger)'
}

const getScoreDescription = (score) => {
  if (score >= 90) return '非常容易理解，适合小学阅读水平'
  if (score >= 80) return '容易理解，适合初中阅读水平'
  if (score >= 70) return '较易理解，适合高中阅读水平'
  if (score >= 60) return '中等难度，适合大学阅读水平'
  if (score >= 50) return '较难理解，适合专业阅读水平'
  return '难以理解，适合学术阅读水平'
}

const pointerPosition = computed(() => {
  const score = props.readability.readabilityScore || 75
  return Math.min(100, Math.max(0, score))
})

const scaleMarkers = [
  { position: 0, label: '0', color: 'var(--el-color-danger)' },
  { position: 25, label: '25', color: 'var(--el-color-danger-light)' },
  { position: 50, label: '50', color: 'var(--el-color-warning)' },
  { position: 75, label: '75', color: 'var(--el-color-success-light)' },
  { position: 100, label: '100', color: 'var(--el-color-success)' }
]

const scoreLegend = [
  '极难 (0-20)',
  '困难 (20-40)',
  '适中 (40-60)',
  '简单 (60-80)',
  '极易 (80-100)'
]

const initScoreChart = () => {
  if (!scoreChartRef.value || !props.readability.scores) return

  scoreChart = echarts.init(scoreChartRef.value)
  const scores = props.readability.scores
  const data = Object.entries(scores).map(([name, value]) => ({
    name: formatScoreName(name),
    value: value
  }))

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const item = params[0]
        return `${item.name}: ${formatValue(item.value)}<br/>${getScoreRangeDesc(item.name, item.value)}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '分数',
      axisLabel: {
        formatter: '{value}'
      },
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'category',
      data: data.map(item => item.name),
      axisLabel: {
        interval: 0,
        formatter: function(value) {
          if (value.length > 12) {
            return value.substring(0, 12) + '...'
          }
          return value
        }
      }
    },
    series: [
      {
        type: 'bar',
        data: data.map(item => ({
          value: item.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: 'rgba(50, 120, 200, 0.6)' },
              { offset: 1, color: 'rgba(50, 120, 200, 0.9)' }
            ])
          }
        })),
        label: {
          show: true,
          position: 'right',
          formatter: function(params) {
            return formatValue(params.value)
          }
        },
        barWidth: '60%',
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: 'rgba(50, 150, 250, 0.8)' },
              { offset: 1, color: 'rgba(50, 150, 250, 1)' }
            ])
          }
        }
      }
    ],
    animationDuration: 1500
  }

  scoreChart.setOption(option)
}

const formatScoreName = (name) => {
  const nameMap = {
    flesch_reading_ease: 'Flesch可读性',
    flesch_kincaid_grade: 'Flesch-Kincaid等级',
    gunning_fog: 'Gunning Fog指数',
    smog: 'SMOG指数',
    automated_readability: '自动可读性指数',
    coleman_liau: 'Coleman-Liau指数',
    dale_chall: 'Dale-Chall指数'
  }
  return nameMap[name] || name
}

const getScoreRangeDesc = (name, value) => {
  if (name.includes('Flesch可读性')) {
    if (value >= 90) return '很容易理解(小学低年级)'
    if (value >= 80) return '容易理解(小学高年级)'
    if (value >= 70) return '相当容易理解(初中)'
    if (value >= 60) return '普通难度(初中到高中)'
    if (value >= 50) return '略有难度(高中)'
    return '难以理解(大学及以上)'
  }
  return ''
}

const initCharts = () => {
  requestAnimationFrame(() => {
    try {
      initScoreChart()
    } catch (error) {
      console.error('Error initializing charts:', error)
    }
  })
}

watch(() => props.readability, () => {
  if (document.visibilityState === 'visible') {
    initCharts()
  }
}, { deep: true })

onMounted(() => {
  setTimeout(initCharts, 0)
  window.addEventListener('resize', initCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', initCharts)
  scoreChart?.dispose()
})
</script>

<style scoped>
.readability-chart {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.chart-container {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.scores-container {
  grid-column: span 2;
}

.text-stats-container {
  grid-column: span 2;
}

.score-summary {
  grid-column: span 2;
}

h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: var(--el-text-color-primary);
  text-align: center;
  position: relative;
}

h3:after {
  content: '';
  display: block;
  width: 50px;
  height: 3px;
  background: var(--el-color-primary-light-5);
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 3px;
}

.chart {
  width: 100%;
  height: 300px;
}

.score-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 30px;
  padding: 20px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 46px;
  font-weight: bold;
  color: white;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  position: relative;
  animation: pulseAnimation 2s infinite;
}

.score-circle:before {
  content: '';
  position: absolute;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  animation: rippleAnimation 2s infinite;
}

@keyframes pulseAnimation {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

@keyframes rippleAnimation {
  0% { transform: scale(0.9); opacity: 1; }
  100% { transform: scale(1.2); opacity: 0; }
}

.score-info {
  flex: 1;
  max-width: 300px;
}

.score-level {
  font-size: 24px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
}

.score-desc {
  font-size: 15px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.reading-scale {
  padding: 20px 10px;
}

.scale-container {
  height: 60px;
  position: relative;
  margin-bottom: 15px;
}

.scale-line {
  position: absolute;
  top: 30px;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(to right, 
    var(--el-color-danger), 
    var(--el-color-warning), 
    var(--el-color-success));
  border-radius: 2px;
}

.scale-marker {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
}

.marker-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  position: absolute;
  top: 26px;
  left: 50%;
  transform: translateX(-50%);
}

.marker-label {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.scale-pointer {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  transition: left 1s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pointer-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--el-color-primary);
  border: 3px solid white;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  position: absolute;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
}

.pointer-value {
  position: absolute;
  top: 45px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 16px;
  font-weight: bold;
  color: var(--el-color-primary);
  background: rgba(255, 255, 255, 0.8);
  padding: 2px 8px;
  border-radius: 10px;
}

.scale-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 30px;
  padding: 0 12px;
}

.scale-labels div {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
  margin-top: 10px;
}

.stat-item {
  background: var(--el-bg-color-page);
  border-radius: 8px;
  padding: 15px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.3s, box-shadow 0.3s;
}

.stat-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  margin-bottom: 10px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--el-color-primary-light-9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-color-primary);
}

.icon-character:before { content: "Aa"; font-weight: bold; }
.icon-word:before { content: "词"; }
.icon-sentence:before { content: "句"; }
.icon-length:before { content: "长"; }
.icon-time:before { content: "⏱"; }
.icon-default:before { content: "?"; }

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.scores-legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 15px;
  margin-top: 15px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .scores-container, .text-stats-container, .score-summary {
    grid-column: span 1;
  }

  .score-display {
    flex-direction: column;
    padding: 15px 10px;
    gap: 15px;
  }

  .score-circle {
    width: 90px;
    height: 90px;
    font-size: 36px;
  }

  .score-circle:before {
    width: 105px;
    height: 105px;
  }

  .score-info {
    text-align: center;
  }

  .stat-item {
    padding: 10px;
  }

  .stat-icon {
    width: 30px;
    height: 30px;
    font-size: 12px;
  }

  .stat-value {
    font-size: 18px;
  }
}
</style> 