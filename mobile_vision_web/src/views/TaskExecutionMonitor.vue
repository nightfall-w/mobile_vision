<template>
  <div class="testplan-execution-container">
    <div class="execution-header">
      <div class="header-left">
        <el-button @click="goBack" size="small">
          <el-icon><Back /></el-icon>
          返回
        </el-button>
        <div class="plan-info">
          <h2>任务执行监控</h2>
          <span class="plan-name">任务 #{{ taskId }}</span>
        </div>
      </div>
      <div class="header-right">
        <el-tag :type="statusTagType" size="large">{{ statusText }}</el-tag>
        <el-button
          v-if="taskState.status === 'running'"
          type="danger"
          size="small"
          @click="stopExecution"
        >
          <el-icon><VideoPause /></el-icon>
          停止执行
        </el-button>
      </div>
    </div>

    <div class="execution-main">
      <div class="left-panel">
        <el-card class="todo-list-card">
          <template #header>
            <div class="todo-header">
              <span>子任务规划</span>
              <span class="todo-count">{{ completedCount }}/{{ taskState.task_list?.length || 0 }} 已完成</span>
            </div>
          </template>
          <div class="todo-list" ref="todoListRef">
            <div
              v-for="(subtask, index) in taskState.task_list"
              :key="subtask.task_id"
              class="todo-item"
              :class="{
                'active': index === taskState.current_task_index,
                'completed': subtask.state === 'completed',
                'failed': subtask.state === 'failed',
                'pending': subtask.state === 'pending'
              }"
            >
              <div class="todo-checkbox">
                <el-icon v-if="subtask.state === 'completed'" class="check-icon success"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="subtask.state === 'failed'" class="check-icon danger"><CircleCloseFilled /></el-icon>
                <el-icon v-else-if="index === taskState.current_task_index" class="check-icon running"><Loading class="rotating" /></el-icon>
                <div v-else class="check-icon pending"></div>
              </div>
              <div class="todo-content">
                <div class="todo-title">
                  <span class="todo-index">{{ index + 1 }}</span>
                  <span class="todo-desc">{{ subtask.description }}</span>
                </div>
                <div v-if="subtask.reason" class="todo-reason">{{ subtask.reason }}</div>
              </div>
              <div class="todo-timestamp">
                <span v-if="subtask.completed_at">{{ formatShortTime(subtask.completed_at) }}</span>
              </div>
            </div>
            <div v-if="!taskState.task_list || taskState.task_list.length === 0" class="empty-tip">
              暂无子任务数据
            </div>
          </div>
        </el-card>

        <el-card class="log-card">
          <template #header>
            <div class="log-header">
              <span>执行日志</span>
              <el-button size="small" text @click="clearLogs">清空</el-button>
            </div>
          </template>
          <div class="log-list" ref="logListRef">
            <div
              v-for="(log, index) in logs"
              :key="index"
              class="log-item"
              :class="log.level"
            >
              <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              <span class="log-level">{{ log.level.toUpperCase() }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
            <div v-if="logs.length === 0" class="empty-tip">暂无日志</div>
          </div>
        </el-card>
      </div>

      <div class="right-panel">
        <el-card class="current-task-card">
          <template #header>
            <div class="current-task-header">
              <span>当前任务执行</span>
              <span v-if="currentSubtask" class="current-task-name">{{ currentSubtask.description }}</span>
            </div>
          </template>
          <div class="step-scroll-container" ref="stepScrollRef">
            <div
              v-for="(step, index) in currentSteps"
              :key="step.step_number || index"
              class="step-item"
              :class="{
                'success': step.success,
                'failed': !step.success && step.step_number,
                'running': isStepRunning(step, index)
              }"
            >
              <div class="step-status">
                <el-icon v-if="step.success" class="step-icon success"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="!step.success && step.step_number" class="step-icon danger"><CircleCloseFilled /></el-icon>
                <el-icon v-else class="step-icon running"><Loading class="rotating" /></el-icon>
              </div>
              <div class="step-main">
                <div class="step-header">
                  <span class="step-number">{{ step.step_number || '--' }}</span>
                  <span class="step-action">{{ step.action || '等待中' }}</span>
                </div>
                <div class="step-desc">{{ step.description || '准备执行下一个步骤...' }}</div>
                <div v-if="step.result" class="step-result">{{ step.result }}</div>
                <div class="step-meta">
                  <span v-if="step.x && step.y" class="step-meta-item">
                    坐标: ({{ step.x }}, {{ step.y }})
                  </span>
                  <span v-if="step.text" class="step-meta-item">
                    文本: {{ step.text }}
                  </span>
                  <span v-if="step.direction" class="step-meta-item">
                    方向: {{ step.direction }}
                  </span>
                  <span v-if="step.timestamp" class="step-meta-time">
                    {{ formatShortTime(step.timestamp) }}
                  </span>
                </div>
              </div>
            </div>
            <div v-if="currentSteps.length === 0" class="empty-steps-tip">
              <el-icon class="empty-icon"><Document /></el-icon>
              <p>等待任务开始...</p>
            </div>
          </div>
        </el-card>

        <el-card class="screenshot-card">
          <template #header>
            <span>设备截图</span>
          </template>
          <div class="screenshot-container">
            <img
              v-if="currentScreenshot"
              :src="'data:image/png;base64,' + currentScreenshot"
              alt="设备截图"
              class="screenshot-img"
            />
            <div v-else class="screenshot-placeholder">
              <el-icon size="48"><Picture /></el-icon>
              <span>暂无截图</span>
            </div>
          </div>
        </el-card>

        <el-card class="progress-card">
          <template #header>
            <span>执行进度</span>
          </template>
          <div class="progress-info">
            <div class="progress-stat">
              <span class="stat-label">总步数：</span>
              <span class="stat-value">{{ taskState.total_steps || 0 }}</span>
            </div>
            <div class="progress-stat success">
              <span class="stat-label">成功：</span>
              <span class="stat-value">{{ taskState.success_steps || 0 }}</span>
            </div>
            <div class="progress-stat failed">
              <span class="stat-label">失败：</span>
              <span class="stat-value">{{ taskState.failed_steps || 0 }}</span>
            </div>
          </div>
          <el-progress
            :percentage="completionPercent"
            :status="progressStatus"
            :stroke-width="12"
          />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Back,
  CircleCheckFilled,
  CircleCloseFilled,
  Loading,
  Document,
  Picture,
  VideoPause
} from '@element-plus/icons-vue'
import axios from '../network/axios'

const router = useRouter()
const route = useRoute()

const taskId = ref(parseInt(route.params.taskId) || 0)
const taskState = ref({
  task_id: taskId.value,
  status: 'pending',
  current_task_index: 0,
  task_list: [],
  current_step: null,
  total_steps: 0,
  success_steps: 0,
  failed_steps: 0
})
const logs = ref([])
const currentScreenshot = ref('')
const todoListRef = ref(null)
const stepScrollRef = ref(null)
const logListRef = ref(null)
let eventSource = null
let screenshotTimer = null

const completedCount = computed(() => {
  return taskState.value.task_list?.filter(t => t.state === 'completed').length || 0
})

const currentSubtask = computed(() => {
  return taskState.value.task_list?.[taskState.value.current_task_index]
})

const currentSteps = computed(() => {
  if (!currentSubtask.value) return []
  return currentSubtask.value.steps || []
})

const statusTagType = computed(() => {
  const status = taskState.value.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'primary'
  return 'info'
})

const statusText = computed(() => {
  const status = taskState.value.status
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'running') return '运行中'
  return '等待中'
})

const completionPercent = computed(() => {
  const total = taskState.value.task_list?.length || 0
  if (total === 0) return 0
  const completed = taskState.value.task_list?.filter(t => t.state === 'completed').length || 0
  return Math.round((completed / total) * 100)
})

const progressStatus = computed(() => {
  if (taskState.value.status === 'failed') return 'exception'
  if (completionPercent.value === 100) return 'success'
  return ''
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return timestamp.split('T')[1]?.split('.')[0] || ''
  }
}

const formatShortTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return timestamp.split('T')[1]?.split(':')[0] + ':' + timestamp.split('T')[1]?.split(':')[1] || ''
  }
}

const isStepRunning = (step, index) => {
  if (step.success) return false
  if (step.step_number) return false
  if (currentSteps.value.length === 0) return false
  const lastStep = currentSteps.value[currentSteps.value.length - 1]
  return index === currentSteps.value.length - 1 && lastStep && !lastStep.step_number
}

const goBack = () => {
  router.back()
}

const clearLogs = () => {
  logs.value = []
}

const stopExecution = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要停止执行吗？',
      '确认停止',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    ElMessage.success('已发送停止指令')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止执行失败:', error)
    }
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (stepScrollRef.value) {
      stepScrollRef.value.scrollTop = stepScrollRef.value.scrollHeight
    }
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
}

const connectSSE = () => {
  const streamUrl = `/api/v1/task/${taskId.value}/stream`
  console.log('连接SSE:', streamUrl)

  eventSource = new EventSource(streamUrl)

  eventSource.addEventListener('state_update', (event) => {
    try {
      const data = JSON.parse(event.data)
      handleStateUpdate(data)
    } catch (e) {
      console.error('解析状态更新失败:', e)
    }
  })

  eventSource.addEventListener('log', (event) => {
    try {
      const data = JSON.parse(event.data)
      handleLog(data)
    } catch (e) {
      console.error('解析日志失败:', e)
    }
  })

  eventSource.onerror = (error) => {
    console.error('SSE错误:', error)
    eventSource.close()
    if (taskState.value.status === 'running') {
      setTimeout(() => {
        connectSSE()
      }, 3000)
    }
  }

  eventSource.onopen = () => {
    console.log('SSE连接成功')
    ElMessage.success('已连接到任务监控')
  }
}

const handleStateUpdate = (data) => {
  if (data.task_id) taskState.value.task_id = data.task_id
  if (data.status) taskState.value.status = data.status
  if (data.current_task_index !== undefined) taskState.value.current_task_index = data.current_task_index
  if (data.task_list) taskState.value.task_list = data.task_list
  if (data.current_step) taskState.value.current_step = data.current_step
  if (data.total_steps !== undefined) taskState.value.total_steps = data.total_steps
  if (data.success_steps !== undefined) taskState.value.success_steps = data.success_steps
  if (data.failed_steps !== undefined) taskState.value.failed_steps = data.failed_steps

  scrollToBottom()
}

const handleLog = (data) => {
  logs.value.push({
    level: data.level,
    message: data.message,
    timestamp: data.timestamp
  })
  scrollToBottom()
}

const fetchScreenshot = async () => {
  try {
    const res = await axios.get(`/api/v1/task/${taskId.value}/screenshot`)
    if (res.code === 0 && res.data && res.data.screenshot_base64) {
      currentScreenshot.value = res.data.screenshot_base64
    }
  } catch (e) {
    console.error('获取截图失败:', e)
  }
}

const fetchInitialState = async () => {
  try {
    const res = await axios.get(`/api/v1/task/${taskId.value}/state`)
    if (res.code === 0 && res.data) {
      handleStateUpdate(res.data)
    }
  } catch (e) {
    console.error('获取初始状态失败:', e)
  }

  try {
    const res = await axios.get(`/api/v1/task/${taskId.value}/logs`)
    if (res.code === 0 && res.data) {
      logs.value = res.data
    }
  } catch (e) {
    console.error('获取日志失败:', e)
  }

  await fetchScreenshot()
}

onMounted(() => {
  fetchInitialState()
  connectSSE()

  screenshotTimer = setInterval(() => {
    if (taskState.value.status === 'running') {
      fetchScreenshot()
    }
  }, 3000)
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
  if (screenshotTimer) {
    clearInterval(screenshotTimer)
  }
})
</script>

<style scoped>
.testplan-execution-container {
  padding: 20px;
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.execution-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  margin-bottom: 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.plan-info {
  display: flex;
  flex-direction: column;
}

.plan-info h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2d3d;
}

.plan-name {
  font-size: 14px;
  color: #909399;
  margin-top: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.execution-main {
  display: flex;
  gap: 20px;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  width: 450px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.todo-list-card, .log-card, .current-task-card, .screenshot-card, .progress-card {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.todo-list-card :deep(.el-card__body),
.log-card :deep(.el-card__body),
.current-task-card :deep(.el-card__body),
.screenshot-card :deep(.el-card__body),
.progress-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.todo-header, .current-task-header, .log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.todo-count {
  font-size: 13px;
  color: #909399;
}

.todo-list, .log-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  margin-bottom: 8px;
  background: #ffffff;
  border: 1px solid #ebeef5;
  transition: all 0.3s ease;
}

.todo-item.active {
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}

.todo-item.completed {
  background: #f0f9eb;
  border-color: #67c23a;
  opacity: 0.85;
}

.todo-item.failed {
  background: #fef0f0;
  border-color: #f56c6c;
}

.todo-item.pending {
  background: #f5f7fa;
  border-color: #e4e7ed;
  opacity: 0.7;
}

.todo-checkbox {
  flex-shrink: 0;
  padding-top: 2px;
}

.check-icon {
  font-size: 22px;
}

.check-icon.success { color: #67c23a; }
.check-icon.danger { color: #f56c6c; }
.check-icon.running { color: #409eff; }
.check-icon.pending {
  width: 22px;
  height: 22px;
  border: 2px solid #dcdfe6;
  border-radius: 50%;
}

.todo-content {
  flex: 1;
  min-width: 0;
}

.todo-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.todo-index {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
}

.todo-desc {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.todo-item.completed .todo-desc {
  text-decoration: line-through;
  color: #909399;
}

.todo-reason {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
}

.todo-timestamp {
  flex-shrink: 0;
  font-size: 12px;
  color: #909399;
  padding-top: 2px;
}

.step-scroll-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.step-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  margin-bottom: 10px;
  background: #ffffff;
  border: 1px solid #ebeef5;
}

.step-item.success {
  border-left: 3px solid #67c23a;
  background: #f0f9eb;
}

.step-item.failed {
  border-left: 3px solid #f56c6c;
  background: #fef0f0;
}

.step-item.running {
  border-left: 3px solid #409eff;
  background: #ecf5ff;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.step-status {
  flex-shrink: 0;
  padding-top: 2px;
}

.step-icon {
  font-size: 22px;
}

.step-icon.success { color: #67c23a; }
.step-icon.danger { color: #f56c6c; }
.step-icon.running { color: #409eff; }

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-main {
  flex: 1;
  min-width: 0;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.step-number {
  font-weight: 600;
  color: #409eff;
  font-size: 13px;
  background: #ecf5ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.step-action {
  font-size: 14px;
  color: #303133;
  font-weight: 600;
}

.step-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
}

.step-result {
  font-size: 12px;
  color: #909399;
  padding: 6px 10px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 6px;
}

.step-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
}

.step-meta-item {
  color: #909399;
}

.step-meta-time {
  color: #c0c4cc;
  margin-left: auto;
}

.log-item {
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.log-item.info {
  background: #f4f4f5;
  color: #606266;
}

.log-item.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.log-item.error {
  background: #fef0f0;
  color: #f56c6c;
}

.log-time {
  color: #909399;
  margin-right: 8px;
}

.log-level {
  font-weight: 600;
  margin-right: 8px;
}

.empty-tip, .empty-steps-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
}

.empty-steps-tip .empty-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}

.empty-steps-tip p {
  margin: 0;
  font-size: 14px;
}

.screenshot-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
}

.screenshot-img {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.screenshot-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #909399;
}

.progress-info {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
}

.progress-stat {
  display: flex;
  gap: 4px;
}

.progress-stat .stat-label {
  font-size: 13px;
  color: #909399;
}

.progress-stat .stat-value {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.progress-stat.success .stat-value { color: #67c23a; }
.progress-stat.failed .stat-value { color: #f56c6c; }
</style>
