<template>
  <div class="job-monitor">
    <!-- 顶部信息栏 -->
    <div class="monitor-header">
      <div class="header-left">
        <el-button @click="goBack" size="default" class="back-btn">
          <el-icon><Back /></el-icon>
          返回
        </el-button>
        <div class="job-info">
          <h1 class="job-title">Job #{{ jobId }}</h1>
          <div class="job-meta">
            <span class="meta-item">
              <el-icon><Document /></el-icon>
              {{ jobDetail.case_name || '加载中...' }}
            </span>
            <span class="meta-item">
              <el-icon><Monitor /></el-icon>
              {{ jobDetail.device_name || '-' }}
            </span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <el-button
          v-if="jobDetail.status === 'running' || jobDetail.status === 'pending'"
          type="danger"
          @click="handleAbortJob"
        >
          放弃任务
        </el-button>
        <el-tag :type="statusTagType" size="large" effect="dark" class="status-tag">
          <el-icon v-if="jobDetail.status === 'running'" class="is-loading"><Loading /></el-icon>
          {{ statusText }}
        </el-tag>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="monitor-main">
      <!-- 左侧区域 - 设备截图 -->
      <div class="left-panel" :style="{ width: containerWidth, maxWidth: '40vw', minWidth: containerWidth, height: containerHeight }">
        <el-card class="screenshot-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><PictureFilled /></el-icon> 设备截图</span>
              <el-button size="small" text @click="refreshScreenshot">
                <el-icon><RefreshRight /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <div class="screenshot-container" :class="{ 'no-screenshot': !currentScreenshot }">
            <img
              v-if="currentScreenshot"
              :src="'data:image/png;base64,' + currentScreenshot"
              alt="设备截图"
              class="screenshot-img"
              ref="screenshotImgRef"
              @load="handleScreenshotLoad"
            />
            <div v-else class="screenshot-placeholder">
              <el-icon size="64"><Picture /></el-icon>
              <span>暂无截图</span>
            </div>
            <div
              v-if="currentScreenshot && showMarker && taskState.current_step?.x && taskState.current_step?.y"
              class="click-marker"
              :style="markerStyle"
            >
              <div class="marker-point"></div>
              <div class="marker-ring"></div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧区域 -->
      <div class="right-panel">
        <!-- 进度统计栏 -->
        <div class="progress-bar-section">
          <div class="progress-info">
            <div class="progress-item">
              <span class="progress-label">子任务进度</span>
              <el-progress
                :percentage="taskProgress"
                :status="progressStatus"
                :stroke-width="12"
                style="width: 200px;"
              />
              <span class="progress-text">{{ completedTaskCount }}/{{ totalTaskCount }} 完成</span>
            </div>
            <div class="stats-group">
              <div class="stat-item success">
                <el-icon><SuccessFilled /></el-icon>
                <span class="stat-value">{{ taskState.success_steps }}</span>
                <span class="stat-label">成功</span>
              </div>
              <div class="stat-item failed">
                <el-icon><CircleCloseFilled /></el-icon>
                <span class="stat-value">{{ taskState.failed_steps }}</span>
                <span class="stat-label">失败</span>
              </div>
              <div class="stat-item total">
                <el-icon><TrendCharts /></el-icon>
                <span class="stat-value">{{ taskState.total_steps }}</span>
                <span class="stat-label">总步骤</span>
              </div>
              <div class="stat-item time">
                <el-icon><Timer /></el-icon>
                <span class="stat-value">{{ formatDuration(duration) }}</span>
                <span class="stat-label">用时</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 上半部分 - 子任务规划 -->
        <el-card class="subtask-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><List /></el-icon> 子任务规划</span>
              <span class="task-count">{{ taskState.task_list?.length || 0 }} 个任务</span>
            </div>
          </template>
          <div class="subtask-list">
            <div
              v-for="(subtask, index) in taskState.task_list"
              :key="subtask.task_id"
              class="subtask-item"
              :class="{
                'active': index === taskState.current_task_index,
                'completed': subtask.state === 'completed',
                'failed': subtask.state === 'failed'
              }"
            >
              <div class="subtask-header" @click="toggleSubtaskExpand(index)">
                <div class="subtask-status">
                  <el-icon v-if="subtask.state === 'completed'" class="status-icon success"><SuccessFilled /></el-icon>
                  <el-icon v-else-if="subtask.state === 'failed'" class="status-icon danger"><CircleCloseFilled /></el-icon>
                  <el-icon v-else-if="index === taskState.current_task_index" class="status-icon running"><Loading /></el-icon>
                  <el-icon v-else class="status-icon pending"><More /></el-icon>
                </div>
                <span class="subtask-index">{{ index + 1 }}</span>
                <span class="subtask-desc">{{ subtask.description }}</span>
                <el-icon class="expand-icon" :class="{ 'expanded': expandedSubtasks.includes(index) }">
                  <ArrowRight />
                </el-icon>
              </div>
              <div v-if="subtask.target_state" class="target-state-row">
                <span class="target-state-item">
                  <el-icon class="target-icon"><Aim /></el-icon>
                  <span class="target-label">任务预期:</span>
                  <span class="target-value">{{ subtask.target_state }}</span>
                </span>
                <span v-if="index === taskState.current_task_index && subtask.steps?.length" class="target-state-item current-step">
                  <el-icon class="current-icon"><Location /></el-icon>
                  <span class="target-label">当前:</span>
                  <span class="target-value">{{ subtask.steps[subtask.steps.length - 1].action }}</span>
                </span>
              </div>

              <div v-if="expandedSubtasks.includes(index) && subtask.steps?.length > 0" class="step-list">
                <div
                  v-for="step in subtask.steps"
                  :key="step.step_number"
                  class="step-item"
                  :class="{ 'success': step.success, 'failed': !step.success }"
                >
                  <span class="step-number">{{ step.step_number }}</span>
                  <span class="step-action">{{ step.action }}</span>
                  <span class="step-desc">{{ step.description }}</span>
                  <el-icon v-if="step.success" class="step-icon success"><SuccessFilled /></el-icon>
                  <el-icon v-else class="step-icon failed"><CircleCloseFilled /></el-icon>
                </div>
                <div v-if="!subtask.steps?.length" class="no-steps">暂无执行步骤</div>
              </div>
            </div>
            <div v-if="!taskState.task_list?.length" class="empty-tip">
              <el-icon size="48"><Document /></el-icon>
              <span>等待任务规划...</span>
            </div>
          </div>
        </el-card>

        <!-- 下半部分 - 执行日志 -->
        <el-card class="log-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span><el-icon><Tickets /></el-icon> 执行日志</span>
              <div class="log-actions">
                <el-button v-if="hasThinkingLogs" size="small" :type="showThinking ? 'warning' : 'default'" text @click="showThinking = !showThinking">
                  <el-icon><Aim /></el-icon> 思考过程
                </el-button>
                <el-button size="small" text @click="clearLogs">清空</el-button>
              </div>
            </div>
          </template>
          <div class="log-list" ref="logListRef">
            <div
              v-for="(log, index) in filteredLogs"
              :key="log._log_id || index"
              class="log-item"
              :class="[log.level?.toLowerCase()]"
            >
              <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
              <span v-if="log.level !== 'THINKING'" class="log-level">{{ log.level }}</span>
              <template v-if="log.level === 'THINKING'">
                <span class="log-level thinking-label">思考</span>
                <span class="log-message thinking-summary" @click="openThinkingDialog(log)">{{ getThinkingSummary(log.message) }}</span>
                <el-button size="small" text class="view-detail-btn" @click="openThinkingDialog(log)">
                  <el-icon><View /></el-icon> 查看详情
                </el-button>
              </template>
              <span v-else class="log-message">{{ log.message }}</span>
            </div>
            <div v-if="logs.length === 0" class="empty-tip">
              <el-icon size="48"><Tickets /></el-icon>
              <span>暂无日志</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 思考详情弹窗 -->
    <el-dialog
      v-model="thinkingDialogVisible"
      title="思考过程详情"
      width="80%"
      :close-on-click-modal="false"
      :show-close="false"
      class="thinking-dialog"
    >
      <template #header>
        <div class="dialog-header">
          <span class="dialog-title"><el-icon><Aim /></el-icon> 思考过程详情</span>
          <el-icon class="close-btn" @click="closeThinkingDialog"><Close /></el-icon>
        </div>
      </template>
      <div class="thinking-dialog-content" v-if="currentThinkingLog">
        <div class="thinking-meta">
          <span class="meta-time"><el-icon><Timer /></el-icon> {{ formatLogTime(currentThinkingLog.timestamp) }}</span>
        </div>
        <div class="thinking-content">
          <pre class="thinking-text">{{ currentThinkingLog.message }}</pre>
        </div>
        <PageStructureViewer v-if="currentThinkingLog.page_structure" :pageData="currentThinkingLog.page_structure" />
      </div>
      <template #footer>
        <el-button @click="closeThinkingDialog">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, SuccessFilled, CircleCloseFilled, Loading, More, Document, Monitor, List, Tickets, PictureFilled, Picture, RefreshRight, Timer, TrendCharts, Aim, Location, View, Close } from '@element-plus/icons-vue'
import axios from '../network/axios'
import { abortTestJob } from '../network/api'
import PageStructureViewer from '../components/PageStructureViewer.vue'

const router = useRouter()
const route = useRoute()

const jobId = ref(parseInt(route.params.jobId) || 0)
const jobDetail = ref({
  case_name: '',
  device_name: '',
  status: 'pending',
  result: ''
})
const taskState = ref({
  task_id: jobId.value,
  status: 'pending',
  current_task_index: 0,
  task_list: [],
  current_step: null,
  current_subtask: null,
  total_steps: 0,
  success_steps: 0,
  failed_steps: 0
})
const logs = ref([])
const showThinking = ref(false)
const hasThinkingLogs = computed(() => logs.value.some(l => l.level === 'THINKING'))
const filteredLogs = computed(() => {
  if (showThinking.value) return logs.value
  return logs.value.filter(l => l.level !== 'THINKING')
})
const currentScreenshot = ref('')
const logListRef = ref(null)
const screenshotImgRef = ref(null)
const expandedSubtasks = ref([])
const thinkingDialogVisible = ref(false)
const currentThinkingLog = ref(null)
const imageScale = ref({ width: 0, height: 0, naturalWidth: 0, naturalHeight: 0 })
const containerWidth = ref('40vw')
const containerHeight = ref('auto')
const currentTime = ref(Date.now())
const jobDuration = ref(0)
const jobEndTime = ref(null)
let stateEventSource = null
let logEventSource = null
let screenshotEventSource = null
let screenshotTimer = null
let durationTimer = null
let startTime = null
let markerTimer = null
let showMarker = ref(true)

const statusTagType = computed(() => {
  const status = jobDetail.value.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'primary'
  if (status === 'aborted') return 'warning'
  return 'info'
})

const statusText = computed(() => {
  const status = jobDetail.value.status
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'running') return '运行中'
  if (status === 'aborted') return '已放弃'
  return '等待中'
})

const taskProgress = computed(() => {
  if (!taskState.value.task_list?.length) return 0
  const completed = taskState.value.task_list.filter(t => t.state === 'completed').length
  return Math.round((completed / taskState.value.task_list.length) * 100)
})

const completedTaskCount = computed(() => {
  return taskState.value.task_list?.filter(t => t.state === 'completed').length || 0
})

const totalTaskCount = computed(() => {
  return taskState.value.task_list?.length || 0
})

const progressStatus = computed(() => {
  if (jobDetail.value.status === 'completed') return 'success'
  if (jobDetail.value.status === 'failed') return 'exception'
  if (taskProgress.value >= 100) return 'success'
  return ''
})

const duration = computed(() => {
  // 任务结束时，使用后端返回的数据
  if (jobDetail.value.status === 'completed' || jobDetail.value.status === 'failed' || jobDetail.value.status === 'aborted') {
    // 优先使用后端返回的 duration
    if (jobDuration.value > 0) {
      return jobDuration.value
    }
    // 如果没有 duration，用 end_time 计算
    if (startTime && jobEndTime.value) {
      return Math.floor((jobEndTime.value - startTime) / 1000)
    }
  }

  // 任务运行中或等待中，实时计算时间
  if (!startTime || jobDetail.value.status === 'pending') return 0
  return Math.floor((currentTime.value - startTime) / 1000)
})

const markerStyle = computed(() => {
  if (!taskState.value.current_step?.x || !taskState.value.current_step?.y) {
    return {}
  }
  let scaledX = taskState.value.current_step.x
  let scaledY = taskState.value.current_step.y

  if (imageScale.value.naturalWidth > 0 && imageScale.value.naturalHeight > 0) {
    const scaleX = imageScale.value.width / imageScale.value.naturalWidth
    const scaleY = imageScale.value.height / imageScale.value.naturalHeight
    const scale = Math.min(scaleX, scaleY)
    scaledX = taskState.value.current_step.x * scale
    scaledY = taskState.value.current_step.y * scale
  }

  return {
    left: scaledX + 'px',
    top: scaledY + 'px'
  }
})

const goBack = () => {
  router.back()
}

const clearLogs = () => {
  logs.value = []
}

const openThinkingDialog = (log) => {
  currentThinkingLog.value = log
  thinkingDialogVisible.value = true
}

const closeThinkingDialog = () => {
  thinkingDialogVisible.value = false
  currentThinkingLog.value = null
}

const getThinkingSummary = (message) => {
  // 取前缀标签和思考内容的前60个字符
  const tag = message.startsWith('[') ? message.match(/^\[.*?\]/)?.[0] || '' : ''
  const content = message.replace(/^\[.*?\]\s*/, '').trim()
  if (content.length <= 60) return `${tag} ${content}`
  return `${tag} ${content.substring(0, 60)}...`
}

const toggleSubtaskExpand = (index) => {
  const idx = expandedSubtasks.value.indexOf(index)
  if (idx > -1) {
    expandedSubtasks.value.splice(idx, 1)
  } else {
    expandedSubtasks.value.push(index)
  }
}

const refreshScreenshot = () => {
  fetchScreenshot()
}

const handleScreenshotLoad = () => {
  nextTick(() => {
    if (screenshotImgRef.value) {
      const { naturalWidth, naturalHeight, offsetWidth, offsetHeight } = screenshotImgRef.value
      const maxWidth = window.innerWidth * 0.4
      const availableHeight = window.innerHeight - 140
      const ratio = naturalHeight / naturalWidth
      let displayWidth = naturalWidth
      let displayHeight = naturalHeight
      if (displayWidth > maxWidth) {
        displayWidth = maxWidth
        displayHeight = maxWidth * ratio
      }
      if (displayHeight > availableHeight) {
        displayHeight = availableHeight
        displayWidth = availableHeight / ratio
      }
      imageScale.value = {
        width: displayWidth,
        height: displayHeight,
        naturalWidth,
        naturalHeight
      }
      containerWidth.value = displayWidth + 'px'
      containerHeight.value = (displayHeight + 50) + 'px'
    }
  })
}

const formatDuration = (seconds) => {
  if (!seconds) return '00:00:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const formatLogTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timestamp.split('T')[1]?.split('.')[0] || ''
  }
}

const connectStateStream = () => {
  const streamUrl = `/api/v1/testtask/job/${jobId.value}/stream`
  console.log('连接状态流:', streamUrl)

  stateEventSource = new EventSource(streamUrl)

  stateEventSource.addEventListener('state_update', (event) => {
    try {
      const data = JSON.parse(event.data)
      handleStateUpdate(data)

      if (data.status === 'completed' || data.status === 'failed' || data.status === 'aborted') {
        jobDetail.value.status = data.status
      }
    } catch (e) {
      console.error('解析状态更新失败:', e)
    }
  })

  stateEventSource.onerror = () => {}

  stateEventSource.onopen = () => {
    console.log('状态流连接已建立')
  }
}

const connectLogStream = () => {
  const streamUrl = `/api/v1/testtask/job/${jobId.value}/logs`
  console.log('连接日志流:', streamUrl)

  logEventSource = new EventSource(streamUrl)

  logEventSource.addEventListener('log_entry', (event) => {
    try {
      const data = JSON.parse(event.data)
      handleNewLog(data)

      if (data._log_id && jobDetail.value.status !== 'running') {
        jobDetail.value.status = jobDetail.value.status
      }
    } catch (e) {
      console.error('解析日志失败:', e)
    }
  })

  logEventSource.onerror = () => {}

  logEventSource.onopen = () => {}
}

const connectScreenshotStream = () => {
  const streamUrl = `/api/v1/testtask/job/${jobId.value}/screenshots`
  console.log('连接截图流:', streamUrl)

  screenshotEventSource = new EventSource(streamUrl)

  screenshotEventSource.addEventListener('screenshot', (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.screenshot_base64) {
        currentScreenshot.value = data.screenshot_base64
      }
    } catch (e) {
      console.error('解析截图失败:', e)
    }
  })

  screenshotEventSource.onerror = () => {}

  screenshotEventSource.onopen = () => {
    console.log('截图流连接已建立')
  }
}

const handleStateUpdate = (data) => {
  const oldStatus = jobDetail.value.status
  if (data.job_id) jobDetail.value.job_id = data.job_id
  if (data.status) jobDetail.value.status = data.status
  if (data.result) jobDetail.value.result = data.result
  if (data.start_time && !startTime) {
    startTime = new Date(data.start_time).getTime()
  }
  if (data.end_time) {
    jobEndTime.value = new Date(data.end_time).getTime()
  }
  if (data.duration) {
    jobDuration.value = data.duration
  }

  // 当任务从 pending 变为 running 时，启动计时
  if (oldStatus === 'pending' && data.status === 'running' && !durationTimer) {
    durationTimer = setInterval(() => {
      currentTime.value = Date.now()
    }, 1000)
  }

  // 当任务结束时，停止计时并关闭 SSE 连接
  if ((oldStatus === 'pending' || oldStatus === 'running') &&
      (data.status === 'completed' || data.status === 'failed' || data.status === 'aborted')) {
    // 停止计时器
    if (durationTimer) {
      clearInterval(durationTimer)
      durationTimer = null
    }
    // 关闭 SSE 连接
    if (stateEventSource) {
      stateEventSource.close()
      stateEventSource = null
    }
    if (logEventSource) {
      logEventSource.close()
      logEventSource = null
    }
    // 关闭截图刷新
    if (screenshotTimer) {
      clearInterval(screenshotTimer)
      screenshotTimer = null
    }
  }

  const prevStep = taskState.value.current_step
  if (data.task_id) taskState.value.task_id = data.task_id
  if (data.status) taskState.value.status = data.status
  if (data.current_task_index !== undefined) taskState.value.current_task_index = data.current_task_index
  if (data.task_list) {
    taskState.value.task_list = data.task_list
    if (data.current_task_index !== undefined && !expandedSubtasks.value.includes(data.current_task_index)) {
      expandedSubtasks.value.push(data.current_task_index)
    }
  }
  if (data.current_step) taskState.value.current_step = data.current_step
  if (data.current_subtask !== undefined) taskState.value.current_subtask = data.current_subtask
  if (data.total_steps !== undefined) taskState.value.total_steps = data.total_steps
  if (data.success_steps !== undefined) taskState.value.success_steps = data.success_steps
  if (data.failed_steps !== undefined) taskState.value.failed_steps = data.failed_steps

  // 重置点击标注显示
  if (data.current_step?.x !== undefined && data.current_step?.y !== undefined) {
    const stepChanged = !prevStep ||
                        prevStep.x !== data.current_step.x ||
                        prevStep.y !== data.current_step.y
    if (stepChanged) {
      resetMarkerTimer()
    }
  }
}

const resetMarkerTimer = () => {
  showMarker.value = true
  if (markerTimer) {
    clearTimeout(markerTimer)
  }
  markerTimer = setTimeout(() => {
    showMarker.value = false
    markerTimer = null
  }, 3000)
}

const handleNewLog = (log) => {
  logs.value.push(log)
  scrollToBottom()
}

const fetchScreenshot = async () => {
  try {
    const res = await axios.get(`/api/v1/testtask/job/${jobId.value}/screenshot`)
    if (res.code === 0 && res.data && res.data.screenshot_base64) {
      currentScreenshot.value = res.data.screenshot_base64
    }
  } catch (e) {
    console.error('获取截图失败:', e)
  }
}

const fetchJobDetail = async () => {
  try {
    const res = await axios.get(`/api/v1/testtask/job/${jobId.value}`)
    if (res.code === 0 && res.data) {
      const status = res.data.status
      jobDetail.value = {
        case_name: res.data.case_name || '',
        device_name: res.data.device_name || '',
        status: status,
        result: res.data.result
      }
      if (res.data.start_time) {
        startTime = new Date(res.data.start_time).getTime()
      }
      if (res.data.end_time) {
        jobEndTime.value = new Date(res.data.end_time).getTime()
      }
      if (res.data.duration) {
        jobDuration.value = res.data.duration
      }
      if (res.data.task_id) {
        taskState.value.task_id = res.data.task_id
      }

      // 如果任务已经结束，不需要启动计时器
      if (status === 'completed' || status === 'failed' || status === 'aborted') {
        if (durationTimer) {
          clearInterval(durationTimer)
          durationTimer = null
        }
      }
    }
  } catch (e) {
    console.error('获取Job详情失败:', e)
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
}

const handleAbortJob = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要放弃这个 Job 吗？这将终止正在运行的测试任务。',
      '确认放弃',
      {
        confirmButtonText: '确定放弃',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await abortTestJob(jobId.value)
    if (res.code === 0) {
      ElMessage.success('Job 已放弃')
      jobDetail.value.status = 'aborted'
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

onMounted(async () => {
  await fetchJobDetail()

  // 页面加载时获取一次截图
  fetchScreenshot()

  // 不管任务状态如何，都建立 SSE 连接获取数据
  connectStateStream()
  connectLogStream()

  // 只有任务还在运行时，才连接截图流
  if (jobDetail.value.status === 'pending' || jobDetail.value.status === 'running') {
    connectScreenshotStream()

    durationTimer = setInterval(() => {
      currentTime.value = Date.now()
    }, 1000)
  } else {
    // 任务已结束，等待 2 秒后关闭连接，确保能获取到数据
    setTimeout(() => {
      if (stateEventSource) {
        stateEventSource.close()
        stateEventSource = null
      }
      if (logEventSource) {
        logEventSource.close()
        logEventSource = null
      }
    }, 2000)
  }
})

onUnmounted(() => {
  if (stateEventSource) {
    stateEventSource.close()
  }
  if (logEventSource) {
    logEventSource.close()
  }
  if (screenshotEventSource) {
    screenshotEventSource.close()
  }
  if (screenshotTimer) {
    clearInterval(screenshotTimer)
  }
  if (durationTimer) {
    clearInterval(durationTimer)
  }
  if (markerTimer) {
    clearTimeout(markerTimer)
  }
})

watch(currentScreenshot, (newVal) => {
  if (!newVal) {
    containerWidth.value = '40vw'
  }
})
</script>

<style scoped>
.job-monitor {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 6px 12px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  overflow: hidden;
}

/* 自定义滚动条 */
:deep(.el-scrollbar__wrap::-webkit-scrollbar),
:deep(.el-card__body::-webkit-scrollbar),
.log-list::-webkit-scrollbar,
.subtask-list::-webkit-scrollbar,
.thinking-dialog-content::-webkit-scrollbar,
:deep(.el-dialog__body::-webkit-scrollbar) {
  width: 6px;
  height: 6px;
}

:deep(.el-scrollbar__wrap::-webkit-scrollbar-track),
:deep(.el-card__body::-webkit-scrollbar-track),
.log-list::-webkit-scrollbar-track,
.subtask-list::-webkit-scrollbar-track,
.thinking-dialog-content::-webkit-scrollbar-track,
:deep(.el-dialog__body::-webkit-scrollbar-track) {
  background: transparent;
  border-radius: 3px;
}

:deep(.el-scrollbar__wrap::-webkit-scrollbar-thumb),
:deep(.el-card__body::-webkit-scrollbar-thumb),
.log-list::-webkit-scrollbar-thumb,
.subtask-list::-webkit-scrollbar-thumb,
.thinking-dialog-content::-webkit-scrollbar-thumb,
:deep(.el-dialog__body::-webkit-scrollbar-thumb) {
  background: #c0c4cc;
  border-radius: 3px;
  transition: background 0.2s;
}

:deep(.el-scrollbar__wrap::-webkit-scrollbar-thumb:hover),
:deep(.el-card__body::-webkit-scrollbar-thumb:hover),
.log-list::-webkit-scrollbar-thumb:hover,
.subtask-list::-webkit-scrollbar-thumb:hover,
.thinking-dialog-content::-webkit-scrollbar-thumb:hover,
:deep(.el-dialog__body::-webkit-scrollbar-thumb:hover) {
  background: #909399;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  margin-bottom: 6px;
  transition: box-shadow 0.3s ease;
}

.monitor-header:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08), 0 2px 6px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  background: linear-gradient(135deg, #409eff 0%, #366fc9 100%);
  color: white;
  border: none;
}

.job-info {
  display: flex;
  flex-direction: column;
}

.job-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2d3d;
}

.job-meta {
  display: flex;
  gap: 16px;
  margin-top: 4px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #909399;
}

.status-tag {
  font-size: 14px;
  padding: 8px 16px;
}

.progress-bar-section {
  padding: 16px 20px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s ease;
  margin-bottom: 0;
}

.progress-bar-section:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08), 0 2px 6px rgba(0, 0, 0, 0.05);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.progress-text {
  font-size: 14px;
  color: #909399;
}

.stats-group {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  transition: all 0.2s ease;
}

.stat-item:hover {
  transform: scale(1.02);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stat-item.success { color: #67c23a; }
.stat-item.failed { color: #f56c6c; }
.stat-item.total { color: #409eff; }
.stat-item.time { color: #e6a23c; }

.stat-value {
  font-size: 18px;
  font-weight: 600;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.monitor-main {
  display: flex;
  gap: 16px;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
  align-self: flex-start;
}

.right-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  height: calc(100vh - 100px);
}

.screenshot-card {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  width: auto;
}

.screenshot-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  border-radius: 0 0 16px 16px;
}

.screenshot-container {
  position: relative;
  width: auto;
  height: 100%;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: auto;
  display: inline-block;
}

.screenshot-container.no-screenshot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40vw;
  min-height: 200px;
}

.screenshot-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}

.subtask-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.subtask-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.log-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 8px;
  display: flex;
  flex-direction: column;
}

:deep(.el-card) {
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s ease, transform 0.2s ease;
  border: none;
}

:deep(.el-card:hover) {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

:deep(.el-card__header) {
  padding: 12px 15px;
  border-bottom: 1px solid #f0f2f5;
  background: linear-gradient(135deg, #fafbfc 0%, #ffffff 100%);
  border-radius: 16px 16px 0 0 !important;
}

:deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.card-header span:first-child {
  display: flex;
  align-items: center;
  gap: 6px;
}

.task-count {
  font-size: 12px;
  font-weight: normal;
  color: #909399;
}

.log-actions {
  display: flex;
  gap: 4px;
  align-items: center;
}

.subtask-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.subtask-item {
  padding: 12px;
  border-radius: 12px;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.subtask-item:hover {
  background: #ecf5ff;
  border-color: #d9ecff;
  transform: translateX(2px);
}

.subtask-item.active {
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  border-color: #409eff;
}

.subtask-item.completed {
  background: #f0f9eb;
  border-color: #67c23a;
}

.subtask-item.failed {
  background: #fef0f0;
  border-color: #f56c6c;
}

.subtask-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.subtask-status {
  display: flex;
  align-items: center;
}

.status-icon {
  font-size: 18px;
}

.status-icon.success { color: #67c23a; }
.status-icon.danger { color: #f56c6c; }
.status-icon.running { color: #409eff; }
.status-icon.pending { color: #909399; }

.subtask-index {
  font-weight: 600;
  color: #409eff;
  min-width: 20px;
}

.subtask-desc {
  flex: 1;
  font-size: 14px;
  color: #303133;
}

.expand-icon {
  transition: transform 0.3s;
  color: #909399;
}

.target-state-row {
  display: flex;
  gap: 16px;
  padding: 4px 0 0 26px;
  font-size: 12px;
}

.target-state-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.target-icon {
  color: #d48806;
  font-size: 13px;
}

.current-icon {
  color: #409eff;
  font-size: 13px;
}

.target-label {
  color: #909399;
  flex-shrink: 0;
}

.target-value {
  color: #303133;
  font-weight: 500;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.step-list {
  margin-top: 10px;
  padding-left: 26px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  background: #ffffff;
  font-size: 13px;
}

.step-item.success {
  border-left: 2px solid #67c23a;
}

.step-item.failed {
  border-left: 2px solid #f56c6c;
}

.step-number {
  font-weight: 600;
  color: #409eff;
  min-width: 20px;
}

.step-action {
  color: #303133;
  font-weight: 500;
  min-width: 50px;
}

.step-desc {
  flex: 1;
  color: #606266;
}

.step-icon {
  font-size: 14px;
}

.step-icon.success { color: #67c23a; }
.step-icon.failed { color: #f56c6c; }

.no-steps {
  color: #909399;
  font-size: 12px;
  text-align: center;
  padding: 8px;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-item {
  padding: 10px 14px;
  border-radius: 8px;
  font-family: 'Monaco', 'Menlo', 'Consolas', 'PingFang SC', 'Microsoft YaHei', monospace;
  font-size: 13px;
  line-height: 1.6;
  display: flex;
  gap: 10px;
  transition: all 0.2s ease;
  margin: 1px 0;
}

.log-item:hover {
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
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

.log-item.debug {
  background: #fafafa;
  color: #909399;
}

.log-item.thinking {
  background: #fff7e6;
  color: #d48806;
  border-left: 3px solid #d48806;
  padding: 6px 12px;
  align-items: center;
}

.log-item.thinking .log-level {
  color: #d48806;
}

.thinking-label {
  font-weight: 600;
  font-size: 12px;
  color: #d48806;
  flex-shrink: 0;
  margin-right: 4px;
}

.thinking-summary {
  font-size: 12px;
  color: #b37400;
  flex: 1;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.view-detail-btn {
  flex-shrink: 0;
  color: #d48806;
  padding: 2px 6px;
  font-size: 12px;
}

.view-detail-btn:hover {
  color: #b37400;
  background: #fff0d6;
}

/* 思考详情弹窗样式 */
.thinking-dialog :deep(.el-dialog) {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 20px rgba(0, 0, 0, 0.1);
}

.thinking-dialog :deep(.el-dialog__header) {
  padding: 0;
  border-bottom: 1px solid #f0f2f5;
  background: linear-gradient(135deg, #fafbfc 0%, #ffffff 100%);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
}

.dialog-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.close-btn {
  cursor: pointer;
  font-size: 22px;
  color: #909399;
  transition: all 0.2s ease;
  padding: 6px;
  border-radius: 8px;
}

.close-btn:hover {
  color: #f56c6c;
  background: #fef0f0;
  transform: rotate(90deg);
}

.thinking-dialog :deep(.el-dialog__body) {
  padding: 24px;
  max-height: 70vh;
  overflow-y: auto;
  background: linear-gradient(135deg, #ffffff 0%, #fafbfc 100%);
}

.thinking-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f0f2f5;
  background: #fafbfc;
}

.thinking-dialog :deep(.el-button) {
  border-radius: 10px;
  padding: 10px 24px;
  transition: all 0.2s ease;
}

.thinking-dialog :deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.thinking-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.thinking-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  color: #909399;
}

.meta-time {
  display: flex;
  align-items: center;
  gap: 4px;
}

.thinking-content {
  background: linear-gradient(135deg, #fafbfc 0%, #f5f7fa 100%);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.03);
}

.thinking-text {
  margin: 0;
  font-size: 13px;
  line-height: 2;
  color: #4a5568;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Monaco', 'Menlo', 'Consolas', 'PingFang SC', 'Microsoft YaHei', monospace;
}

/* 弹窗内页面结构可视化优化 */
.thinking-dialog :deep(.page-structure-viewer) {
  margin-top: 16px;
  background: #ffffff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.log-time {
  color: #909399;
  white-space: nowrap;
}

.log-level {
  font-weight: 600;
  white-space: nowrap;
}

.log-message {
  flex: 1;
  word-break: break-all;
}

.screenshot-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #909399;
  gap: 8px;
}

.click-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.marker-point {
  width: 12px;
  height: 12px;
  background: rgba(255, 0, 0, 0.8);
  border-radius: 50%;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.marker-ring {
  width: 30px;
  height: 30px;
  border: 2px solid rgba(255, 0, 0, 0.8);
  border-radius: 50%;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.empty-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  gap: 8px;
}

.empty-icon {
  color: #dcdfe6;
}
</style>
