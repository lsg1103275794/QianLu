<template>
  <div class="sentiment-chart">
    <div class="assessment-summary">
      <div class="assessment-item">
        <div :class="['assessment-value', assessmentClass]">{{ sentiment.assessment || '中性' }}</div>
        <div class="assessment-label">情感评估</div>
      </div>
      <div class="assessment-item">
        <div class="assessment-value">{{ formatValue(sentiment.polarity) }}</div>
        <div class="assessment-label">极性值</div>
      </div>
      <div class="assessment-item">
        <div class="assessment-value">{{ formatValue(sentiment.subjectivity) }}</div>
        <div class="assessment-label">主观性</div>
      </div>
    </div>
    
    <div class="chart-container">
      <h3>情感极性</h3>
      <div ref="polarityChartRef" class="chart"></div>
    </div>
    <div class="chart-container">
      <h3>主观性分析</h3>
      <div ref="subjectivityChartRef" class="chart"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  sentiment: {
    type: Object,
    required: true
  }
})

const formatValue = (value) => {
  if (value === undefined || value === null) return '0.00';
  return Number(value).toFixed(2);
};

const assessmentClass = computed(() => {
  if (!props.sentiment || !props.sentiment.assessment) return 'neutral';
  
  const assessment = props.sentiment.assessment;
  if (assessment.includes('积极')) return 'positive';
  if (assessment.includes('消极')) return 'negative';
  return 'neutral';
});

const polarityChartRef = ref(null)
const subjectivityChartRef = ref(null)
let polarityChart = null
let subjectivityChart = null

const initPolarityChart = () => {
  if (!polarityChartRef.value) return;
  
  if (polarityChart) {
    polarityChart.dispose();
  }

  polarityChart = echarts.init(polarityChartRef.value);
  
  const value = props.sentiment && typeof props.sentiment.polarity === 'number' 
    ? props.sentiment.polarity 
    : 0;
  
  console.log("初始化情感极性图表，值:", value);

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: -1,
        max: 1,
        splitNumber: 8,
        axisLine: {
          lineStyle: {
            width: 30,
            color: [
              [-0.5, '#ff6e76'],
              [0, '#fddd60'],
              [0.5, '#7cffb2'],
              [1, '#58d9f9']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'auto'
          }
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'auto',
            width: 2
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 5
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 14,
          distance: -60,
          formatter: function (value) {
            if (value === -1) return '消极'
            if (value === 0) return '中性'
            if (value === 1) return '积极'
            return ''
          }
        },
        title: {
          offsetCenter: [0, '-20%'],
          fontSize: 16
        },
        detail: {
          fontSize: 20,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: function (value) {
            return Math.round(value * 100) / 100
          },
          color: 'auto'
        },
        data: [
          {
            value: value,
            name: '情感极性'
          }
        ]
      }
    ]
  }

  polarityChart.setOption(option)
}

const initSubjectivityChart = () => {
  if (!subjectivityChartRef.value) return;
  
  if (subjectivityChart) {
    subjectivityChart.dispose();
  }

  subjectivityChart = echarts.init(subjectivityChartRef.value);
  
  const value = props.sentiment && typeof props.sentiment.subjectivity === 'number' 
    ? props.sentiment.subjectivity 
    : 0;
  
  console.log("初始化主观性图表，值:", value);

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 1,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 30,
            color: [
              [0.2, '#58d9f9'],
              [0.8, '#7cffb2'],
              [1, '#fddd60']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'auto'
          }
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'auto',
            width: 2
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 5
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 14,
          distance: -60,
          formatter: function (value) {
            if (value === 0) return '客观'
            if (value === 0.5) return '中性'
            if (value === 1) return '主观'
            return ''
          }
        },
        title: {
          offsetCenter: [0, '-20%'],
          fontSize: 16
        },
        detail: {
          fontSize: 20,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: function (value) {
            return Math.round(value * 100) / 100
          },
          color: 'auto'
        },
        data: [
          {
            value: value,
            name: '主观性'
          }
        ]
      }
    ]
  }

  subjectivityChart.setOption(option)
}

const initCharts = () => {
  requestAnimationFrame(() => {
    try {
      console.log("初始化情感分析图表，数据:", props.sentiment);
      initPolarityChart();
      initSubjectivityChart();
    } catch (error) {
      console.error('Error initializing sentiment charts:', error);
    }
  });
};

watch(() => props.sentiment, (newVal) => {
  console.log("情感数据变化:", newVal);
  if (document.visibilityState === 'visible') {
    initCharts();
  }
}, { deep: true });

const handleResize = () => {
  polarityChart?.resize();
  subjectivityChart?.resize();
};

onMounted(() => {
  setTimeout(initCharts, 100);
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  polarityChart?.dispose();
  subjectivityChart?.dispose();
});
</script>

<style scoped>
.sentiment-chart {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.assessment-summary {
  display: flex;
  justify-content: space-around;
  align-items: center;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 20px 15px;
}

.assessment-item {
  text-align: center;
  min-width: 80px;
}

.assessment-value {
  font-size: 22px;
  font-weight: bold;
  margin-bottom: 5px;
  color: var(--el-color-info);
}

.assessment-value.positive {
  color: var(--el-color-success);
}

.assessment-value.negative {
  color: var(--el-color-danger);
}

.assessment-value.neutral {
  color: var(--el-color-warning);
}

.assessment-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
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
  text-align: center;
  position: relative;
}

h3:after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background: var(--el-color-primary-light-5);
  border-radius: 2px;
}

.chart {
  width: 100%;
  height: 300px;
}

@media (min-width: 768px) {
  .sentiment-chart {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
  }
  
  .assessment-summary {
    grid-column: 1 / -1;
  }
}
</style> 