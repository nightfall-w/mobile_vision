<template>
  <div class="workspace-detail">
    <div class="sticky-header">
      <el-card class="header-card rounded-xl shadow-md border-0 overflow-hidden">
        <div class="page-header-content">
          <div class="header-left">
            <h1 class="page-title">工作空间概览</h1>
            <p class="page-subtitle">管理工作空间的资源和执行统计</p>
          </div>
          <div class="header-right">
            <div class="workspace-info">
              <span class="info-label">当前空间：</span>
              <span class="info-value font-medium">{{ workspaceData.name }}</span>
            </div>
            <el-tag v-for="manager in workspaceData.managers" :key="manager.username" size="small" class="manager-tag">
              <el-icon class="mr-1" :size="12"><User/></el-icon>
              管理员：{{ manager.nickname }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <div class="scroll-content">
      <!-- 周期 Tab -->
      <div class="period-tabs">
        <button v-for="p in periods" :key="p.value" @click="switchPeriod(p.value)" :class="['period-tab', currentPeriod === p.value ? 'active' : '']">
          {{ p.label }}
        </button>
      </div>

      <!-- 统计卡片行 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon blue">
            <el-icon :size="24"><List/></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ periodData.new_cases }}</div>
            <div class="stat-label">新增用例</div>
            <div class="stat-delta">
              <span class="delta-num">{{ periodData.active_cases }}</span>
              <span class="delta-label">活跃</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green">
            <el-icon :size="24"><Folder/></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ periodData.new_plans }}</div>
            <div class="stat-label">新增计划</div>
            <div class="stat-delta">
              <span class="delta-num">{{ periodData.active_plans }}</span>
              <span class="delta-label">活跃</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon purple">
            <el-icon :size="24"><VideoPlay/></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ periodData.executions }}</div>
            <div class="stat-label">执行次数</div>
            <div class="stat-delta">
              <span class="delta-num">{{ periodData.success_rate }}%</span>
              <span class="delta-label">成功率</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 图表行 -->
      <div class="charts-row">
        <el-card class="chart-card rounded-xl shadow-md border-0">
          <template #header>
            <h3 class="card-title">用例优先级分布</h3>
          </template>
          <div ref="priorityChartRef" class="chart-container"></div>
        </el-card>
        <el-card class="chart-card rounded-xl shadow-md border-0">
          <template #header>
            <h3 class="card-title">执行状态分布</h3>
          </template>
          <div ref="statusChartRef" class="chart-container"></div>
        </el-card>
      </div>

      <!-- 底部信息栏 -->
      <div class="footer-bar">
        <span class="footer-item">
          <el-icon :size="14"><User/></el-icon>
          {{ statistics.total_members }} 位成员
        </span>
        <span class="footer-divider">|</span>
        <span class="footer-item">管理员：
          <span v-for="(m, i) in workspaceData.managers" :key="m.username">
            {{ m.nickname }}<span v-if="i < workspaceData.managers.length - 1">、</span>
          </span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { User, List, Folder, VideoPlay } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { getWorkspaceDetail } from '@/network/api.js';

const workspaceData = ref({ id: '', name: '', managers: [] });

const statistics = ref({
  total_cases: 0,
  total_plans: 0,
  active_plans: 0,
  total_executions: 0,
  total_members: 0,
  case_by_level: {},
  execution_by_status: {},
  period_data: { new_cases: 0, active_cases: 0, new_plans: 0, active_plans: 0, executions: 0, success_rate: 0 },
  period_charts: { case_by_level: {}, execution_by_status: {} }
});

const currentPeriod = ref('total');
const periods = [
  { label: '全部', value: 'total' },
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' }
];

const periodData = computed(() => {
  return statistics.value.period_data || { new_cases: 0, active_cases: 0, new_plans: 0, active_plans: 0, executions: 0, success_rate: 0 };
});

const priorityChartRef = ref(null);
const statusChartRef = ref(null);
let priorityChart = null;
let statusChart = null;

const loadStatistics = async () => {
  const workspaceId = window.location.pathname.split('/')[2];
  try {
    const res = await getWorkspaceDetail({ workspace_id: workspaceId, period: currentPeriod.value });
    if (res.code === 0) {
      workspaceData.value = {
        id: res.data.workspace_id,
        name: res.data.workspace_name,
        managers: res.data.manager || []
      };

      const statData = res.data.statistics || {};
      statistics.value = {
        total_cases: statData.total_cases || 0,
        total_plans: statData.total_plans || 0,
        active_plans: statData.active_plans || 0,
        total_executions: statData.total_executions || 0,
        total_members: statData.total_members || 0,
        case_by_level: statData.case_by_level || {},
        execution_by_status: statData.execution_by_status || {},
        period_data: statData.period_data || { new_cases: 0, active_cases: 0, new_plans: 0, active_plans: 0, executions: 0, success_rate: 0 },
        period_charts: statData.period_charts || { case_by_level: {}, execution_by_status: {} },
      };

      await nextTick();
      updateCharts();
    } else {
      ElMessage.error(res.message || '获取统计数据失败');
    }
  } catch (error) {
    console.error('获取统计数据失败:', error);
    ElMessage.error('获取统计数据失败');
  }
};

const switchPeriod = (period) => {
  currentPeriod.value = period;
  loadStatistics();
};

const initCharts = () => {
  if (priorityChartRef.value && !priorityChart) {
    priorityChart = echarts.init(priorityChartRef.value);
  }
  if (statusChartRef.value && !statusChart) {
    statusChart = echarts.init(statusChartRef.value);
  }
};

const updateCharts = () => {
  initCharts();
  
  if (priorityChart) {
    const levelData = statistics.value.period_charts.case_by_level || {};
    priorityChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['P0', 'P1', 'P2', 'P3'], axisLabel: { fontSize: 12 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 12 } },
      series: [{
        name: '用例数',
        type: 'bar',
        barWidth: '50%',
        data: [
          { value: levelData.P0 || 0, itemStyle: { color: '#ef4444' } },
          { value: levelData.P1 || 0, itemStyle: { color: '#f59e0b' } },
          { value: levelData.P2 || 0, itemStyle: { color: '#3b82f6' } },
          { value: levelData.P3 || 0, itemStyle: { color: '#22c55e' } }
        ],
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }]
    });
  }

  if (statusChart) {
    const execData = statistics.value.period_charts.execution_by_status || {};
    statusChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, left: 'center' },
      series: [{
        name: '执行状态',
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: execData.pending || 0, name: '待执行', itemStyle: { color: '#3b82f6' } },
          { value: execData.running || 0, name: '执行中', itemStyle: { color: '#f59e0b' } },
          { value: execData.completed || 0, name: '已完成', itemStyle: { color: '#22c55e' } },
          { value: execData.failed || 0, name: '失败', itemStyle: { color: '#ef4444' } },
          { value: execData.aborted || 0, name: '已放弃', itemStyle: { color: '#6b7280' } }
        ].filter(item => item.value > 0)
      }]
    });
  }
};

onMounted(() => {
  loadStatistics();
});
</script>

<style scoped>
.workspace-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f5f5f5;
  padding-bottom: 10px;
}

.scroll-content {
  flex: 1;
  overflow-y: auto;
  padding-top: 10px;
}

.header-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

.page-header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  padding: 1rem;
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
  color: #1f2937;
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  color: #6b7280;
  margin: 4px 0 0;
}

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.workspace-info {
  font-size: 12px;
  color: #6b7280;
}

.info-label {
  color: #9ca3af;
}

.info-value {
  color: #1f2937;
}

.manager-tag {
  background: #dbeafe;
  color: #2563eb;
  border: none;
}

.period-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  background: #ffffff;
  border-radius: 10px;
  padding: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.period-tab {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.25s;
}

.period-tab:hover {
  color: #3b82f6;
  background: #f0f5ff;
}

.period-tab.active {
  background: #3b82f6;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.blue {
  background: #dbeafe;
  color: #2563eb;
}

.stat-icon.green {
  background: #dcfce7;
  color: #16a34a;
}

.stat-icon.purple {
  background: #ede9fe;
  color: #7c3aed;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #1f2937;
  line-height: 1.1;
  margin-bottom: 2px;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 8px;
}

.stat-delta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.delta-num {
  font-weight: 600;
  color: #22c55e;
}

.delta-label {
  color: #9ca3af;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
  .stats-row {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  min-height: 260px;
}

.chart-container {
  width: 100%;
  height: 200px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.footer-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  font-size: 12px;
  color: #6b7280;
}

.footer-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.footer-divider {
  color: #e5e7eb;
}

:deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: none;
}

:deep(.el-card__body) {
  padding: 16px;
}
</style>
