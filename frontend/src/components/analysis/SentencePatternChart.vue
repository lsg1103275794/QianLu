<template>
  <div class="sentence-pattern-chart">
    <div v-if="!hasValidData" class="empty-data">
      <el-empty description="无句式分析数据" :image-size="80">
        <template #description>
          <p>未能获取有效的句式数据，请检查文本内容或重新分析。</p>
        </template>
      </el-empty>
    </div>
    
    <template v-else>
      <div class="chart-container">
        <h3>句子类型分布</h3>
        <div ref="typeChartRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h3>句子长度分布</h3>
        <div ref="lengthChartRef" class="chart"></div>
      </div>
      
      <!-- 添加句子信息和例句 -->
      <div class="sentence-info">
        <div class="info-item">
          <strong>句子总数:</strong> {{ sentencePattern.sentenceCount || 0 }}
        </div>
        <div class="info-item">
          <strong>平均句长:</strong> {{ sentencePattern.avgSentenceLength || 0 }} 字符
        </div>
        
        <div v-if="sentencePattern.sentences && sentencePattern.sentences.length > 0" class="example-sentences">
          <h4>示例句子:</h4>
          <ul>
            <li v-for="(sentence, index) in sentencePattern.sentences" :key="index">{{ sentence }}</li>
          </ul>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  sentencePattern: {
    type: Object,
    required: true
  }
})

const typeChartRef = ref(null)
const lengthChartRef = ref(null)
let typeChart = null
let lengthChart = null

// 添加一个计算属性来处理有效的句式分析数据
const hasValidData = computed(() => {
  return props.sentencePattern && 
    (props.sentencePattern.sentenceTypes || props.sentencePattern.lengthDistribution);
})

const initTypeChart = () => {
  if (!typeChartRef.value || !props.sentencePattern.sentenceTypes) return

  typeChart = echarts.init(typeChartRef.value)
  const data = Object.entries(props.sentencePattern.sentenceTypes)
    .map(([name, value]) => {
      // 类型名称转换为更友好的中文名称
      const nameMap = {
        'declarative': '陈述句',
        'interrogative': '疑问句',
        'exclamatory': '感叹句',
        'imperative': '祈使句'
      }
      return { 
        name: nameMap[name] || name, 
        value: parseFloat(value) 
      }
    })
    .sort((a, b) => b.value - a.value)

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}% ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      type: 'scroll'
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: data
      }
    ]
  }

  typeChart.setOption(option)
}

const initLengthChart = () => {
  if (!lengthChartRef.value || !props.sentencePattern.lengthDistribution) return

  lengthChart = echarts.init(lengthChartRef.value)
  const data = Object.entries(props.sentencePattern.lengthDistribution)
    .map(([length, count]) => ({ name: length, value: parseFloat(count) }))
    .sort((a, b) => {
      // 按照句子长度范围排序
      const orderMap = {
        '短句(≤10字)': 1,
        '中句(11-30字)': 2,
        '长句(31-50字)': 3,
        '超长句(>50字)': 4
      }
      return orderMap[a.name] - orderMap[b.name]
    })

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        const [param] = params
        return `${param.name}: ${param.value}%`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: '句子长度',
      data: data.map(item => item.name),
      axisLabel: {
        interval: 0,
        rotate: 30
      }
    },
    yAxis: {
      type: 'value',
      name: '百分比 (%)'
    },
    series: [
      {
        type: 'bar',
        data: data.map(item => item.value),
        itemStyle: {
          color: function(params) {
            // 不同长度的句子使用不同颜色
            const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666'];
            return colors[params.dataIndex % colors.length];
          }
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%'
        }
      }
    ]
  }

  lengthChart.setOption(option)
}

const initCharts = () => {
  requestAnimationFrame(() => {
    try {
      initTypeChart()
      initLengthChart()
    } catch (error) {
      console.error('Error initializing charts:', error)
    }
  })
}

watch(() => props.sentencePattern, () => {
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
  typeChart?.dispose()
  lengthChart?.dispose()
})
</script>

<style scoped>
.sentence-pattern-chart {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-data {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 20px;
}

.chart-container {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
}

h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.chart {
  width: 100%;
  height: 300px;
}

.sentence-info {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
}

.info-item {
  margin-bottom: 10px;
}

.example-sentences {
  margin-top: 15px;
}

.example-sentences h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.example-sentences ul {
  padding-left: 20px;
  margin: 0;
}

.example-sentences li {
  margin-bottom: 8px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
}

@media (min-width: 768px) {
  .sentence-pattern-chart {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    grid-template-areas: 
      "type length"
      "info info";
  }
  
  .chart-container:nth-child(1) {
    grid-area: type;
  }
  
  .chart-container:nth-child(2) {
    grid-area: length;
  }
  
  .sentence-info {
    grid-area: info;
  }

  .empty-data {
    grid-column: 1 / -1;
    min-height: 300px;
  }
}
</style> 