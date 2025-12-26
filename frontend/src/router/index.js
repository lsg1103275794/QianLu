import { createRouter, createWebHistory } from 'vue-router'

// Update dynamic imports to use new component paths
const TextAnalysis = () => import('../components/analysis/TextAnalysis.vue')
const StyleTransfer = () => import('../components/style/StyleTransfer.vue')
const ApiManager = () => import('../components/api/ApiManager.vue')
// ModelTest is now in common, not a top-level route view typically
// const ModelTest = () => import('../components/common/ModelTest.vue') 
const WritingStyleAnalysis = () => import('../components/analysis/WritingStyleAnalysis.vue')
const ModelTestView = () => import('../views/ModelTestView.vue') 
// Import the Data Terminal view using the correct relative path
const DataTerminal = () => import('../../src/views/DataTerminal.vue')
const ReportGeneratorView = () => import('../views/ReportGeneratorView.vue')


const routes = [
  {
    path: '/',
    redirect: '/text-analysis' // 默认重定向到文本分析页面
  },
  {
    path: '/text-analysis',
    name: 'text-analysis', 
    component: TextAnalysis
  },
  {
    path: '/style-transfer',
    name: 'style-transfer', 
    component: StyleTransfer
  },
  {
    path: '/settings-manager',
    name: 'settings-manager',
    component: ApiManager
  },
  
  {
    path: '/writing-style-analysis',
    name: 'writing-style-analysis',
    component: WritingStyleAnalysis
  },
  {
    path: '/model-test',
    name: 'model-test',
    component: ModelTestView
  },
  {
    path: '/settings',
    redirect: '/settings-manager'
  },
  // 旧的api-settings路由重定向到新的settings-manager路由
  {
    path: '/api-settings',
    redirect: '/settings-manager'
  },
  // Add the route for Data Terminal
  {
    path: '/data-terminal',
    name: 'data-terminal',
    component: DataTerminal
  },
  // Add the new route for Report Generator
  {
    path: '/report-generator',
    name: 'report-generator',
    component: ReportGeneratorView
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL), // 使用 process.env.BASE_URL for correct base path
  routes
})

export default router