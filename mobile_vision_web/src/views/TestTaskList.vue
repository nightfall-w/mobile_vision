<template>
  <div class="testtask-management">
    <div class="sticky-header">
      <div class="ttl-header-card">
        <div class="ttl-header-inner">
          <div class="ttl-title-group">
            <div class="ttl-icon-wrap"><el-icon :size="18"><List /></el-icon></div>
            <div>
              <h1 class="ttl-title">测试任务</h1>
              <p class="ttl-subtitle">查看测试任务列表与状态</p>
            </div>
          </div>
          <div class="ttl-header-actions">
            <div class="header-info">
              <p class="info-text">当前空间：<span class="font-medium">{{ workspaceName }}</span></p>
              <el-tag
                v-if="managers.length > 0"
                size="small"
                class="manager-tag"
              >
                <el-icon class="mr-1" :size="12"><User/></el-icon>
                管理员：{{ managerNames }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索任务名称"
        class="search-input"
        @keyup.enter="fetchTasks"
      >
        <template #prefix>
          <el-icon><Search/></el-icon>
        </template>
      </el-input>
      <el-select
        v-model="searchForm.plan_id"
        placeholder="选择测试计划"
        class="search-select"
      >
        <el-option label="全部" value="" />
        <el-option v-for="plan in planOptions" :key="plan.plan_id" :label="plan.name" :value="plan.plan_id" />
      </el-select>
      <el-select
        v-model="searchForm.status"
        placeholder="选择状态"
        class="search-select"
      >
        <el-option label="全部" value="" />
        <el-option label="等待中" value="pending" />
        <el-option label="执行中" value="running" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-button @click="fetchTasks" class="search-btn">
        <el-icon><Search/></el-icon>
        查询
      </el-button>
      <el-button @click="resetSearch" class="reset-btn">
        <el-icon><Refresh/></el-icon>
        重置
      </el-button>
      <el-button type="primary" @click="refreshTasks" style="margin-left: auto">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    </div>

    <div class="scroll-content">
    <div class="table-container">
      <el-table
        :data="taskList"
        v-loading="loading"
        element-loading-text="加载中..."
        style="width: 100%"
        :cell-style="{ textAlign: 'center' }"
        :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
        stripe
        empty-text="暂无测试任务"
        row-key="task_id"
        height="100%"
      >
        <el-table-column label="任务ID" width="100">
          <template #default="{ row }">
            <span class="id-text">#{{ row.task_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="任务进度" width="220">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="getProgressStatus(row.status)"
              :stroke-width="10"
            />
            <span class="progress-text">{{
                row.completed_jobs + row.failed_jobs + row.aborted_jobs
              }}/{{ row.total_jobs }} 已完成</span>
          </template>
        </el-table-column>
        <el-table-column label="Job状态" width="280">
          <template #default="{ row }">
            <div class="job-stats">
              <el-tag type="success" size="small">成功 {{ row.completed_jobs }}</el-tag>
              <el-tag type="primary" size="small" v-if="row.running_jobs > 0">执行中 {{ row.running_jobs }}</el-tag>
              <el-tag type="danger" size="small" v-if="row.failed_jobs > 0">失败 {{ row.failed_jobs }}</el-tag>
              <el-tag type="warning" size="small" v-if="row.aborted_jobs > 0">放弃 {{ row.aborted_jobs }}</el-tag>
              <el-tag type="info" size="small" v-if="row.total_jobs - row.completed_jobs - row.failed_jobs - row.aborted_jobs > 0">
                等待 {{ row.total_jobs - row.completed_jobs - row.failed_jobs - row.aborted_jobs - row.running_jobs }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small" effect="dark">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="author_name" label="创建人" min-width="100" />
        <el-table-column label="总用时" width="100">
          <template #default="{ row }">
            <span class="duration-text">{{ formatDuration(row.total_duration) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <span class="action-btn action-view" @click="showJobDetail(row)">查看</span>
              <span
                v-if="row.status === 'running' || row.status === 'pending'"
                class="action-btn action-run"
                @click="handleAbortTask(row)"
              >放弃</span>
              <span
                v-if="row.status !== 'running'"
                class="action-btn action-delete"
                @click="handleDeleteTask(row)"
              >删除</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    </div>
    <div class="ttl-page-footer">
      <el-pagination
        v-model:current-page="pagination.page_num"
        v-model:page-size="pagination.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        background
        small
      />
    </div>
  </div>

  <el-dialog
    v-model="deleteTaskDialogVisible"
    title="确认删除"
    width="400px"
    :close-on-click-modal="false"
  >
    <div class="text-center py-4">
      <el-icon :size="48" class="text-red-500 mb-4"><Warning/></el-icon>
      <p class="text-gray-700">确定要删除任务 <strong>{{ deleteTaskData?.task_name }}</strong> 吗？</p>
      <p class="text-gray-500 text-sm mt-2">此操作不可撤销，请谨慎操作</p>
    </div>
    <template #footer>
      <div class="flex justify-end gap-3">
        <el-button @click="deleteTaskDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDeleteTask">确定删除</el-button>
      </div>
    </template>
  </el-dialog>

  <el-dialog
    v-model="jobDialogVisible"
    :title="'任务详情 - ' + (jobDialogTask?.task_name || '')"
    width="820px"
    top="4vh"
    :close-on-click-modal="false"
    destroy-on-close
    class="jd-dialog"
  >
    <template #header="{ close, titleId, titleClass }">
      <div class="jd-dialog-header">
        <div class="jd-dialog-header-left">
          <div class="jd-dialog-header-icon"><el-icon :size="18"><List /></el-icon></div>
          <div>
            <h3 :id="titleId" :class="titleClass" class="jd-dialog-title">{{ jobDialogTask?.task_name || '任务详情' }}</h3>
            <p class="jd-dialog-subtitle">共 {{ jobDialogTask?.jobs?.length || 0 }} 个Job</p>
          </div>
        </div>
        <div class="jd-dialog-header-right">
          <div class="jd-summary-stats">
            <span class="jd-stat jd-stat-success">{{ jobCompletedCount }} 成功</span>
            <span class="jd-stat jd-stat-running">{{ jobRunningCount }} 执行中</span>
            <span class="jd-stat jd-stat-danger">{{ jobFailedCount }} 失败</span>
            <span class="jd-stat jd-stat-warning">{{ jobAbortedCount }} 放弃</span>
            <span class="jd-stat jd-stat-info">{{ jobPendingCount }} 等待</span>
          </div>
          <el-button class="jd-close-btn" :icon="Close" circle size="small" @click="close" />
        </div>
      </div>
    </template>

    <div v-if="jobDialogTask?.jobs && jobDialogTask.jobs.length > 0" class="jd-dialog-body">
      <div v-for="job in jobDialogTask.jobs" :key="job.job_id" class="jd-card" :class="'jd-card--' + (job.status || 'pending')">
        <div class="jd-card-inner">
          <div class="jd-card-top">
            <div class="jd-card-top-left">
              <span class="jd-card-badge" :style="{ background: getJobBadgeColor(job.status) }">
                #{{ job.job_id }}
              </span>
              <span class="jd-card-name">{{ job.case_name }}</span>
            </div>
            <div class="jd-card-top-right">
              <el-tag :type="getJobStatusType(job.status)" size="small" effect="dark" class="jd-card-status-tag">
                {{ getStatusText(job.status) }}
              </el-tag>
              <el-button type="primary" size="small" @click="monitorJob(job)" class="jd-card-btn">
                <el-icon :size="12"><Monitor /></el-icon>
                监控
              </el-button>
            </div>
          </div>
          <div class="jd-card-divider"></div>
          <div class="jd-card-bottom">
            <span class="jd-meta" title="设备">
              <el-icon :size="13"><Monitor /></el-icon>
              <span>{{ job.device_name || '动态分配' }}</span>
            </span>
            <span class="jd-meta" title="LLM">
              <el-icon :size="13"><Cpu /></el-icon>
              <span>{{ job.llm_name || '-' }}</span>
            </span>
            <span class="jd-meta" title="推理强度">
              <el-icon :size="13"><TrendCharts /></el-icon>
              <span>{{ job.reasoning_effort || 'low' }}</span>
            </span>
            <span class="jd-meta" v-if="job.duration" title="耗时">
              <el-icon :size="13"><Timer /></el-icon>
              <span>{{ formatDuration(job.duration) }}</span>
            </span>
            <span class="jd-meta" v-if="job.start_time" title="开始时间">
              <el-icon :size="13"><Clock /></el-icon>
              <span>{{ job.start_time }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="jd-empty">
      <el-icon :size="40"><List /></el-icon>
      <p>该任务暂无Job</p>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeMount, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, User, Warning, Close, List, Monitor, Cpu, TrendCharts, Timer, View, Clock } from '@element-plus/icons-vue'
import axios from '../network/axios'
import { abortTestTask, deleteTestTask, getWorkspaceDetail } from '../network/api'

const router = useRouter()
const route = useRoute()

const props = defineProps({
  id: {
    type: String,
    default: ''
  }
})

const taskList = ref([])
const loading = ref(false)
const total = ref(0)
const planOptions = ref([])

const filterWorkspaceId = ref('')
const searchKeyword = ref('')

const pagination = reactive({
  page_num: 1,
  page_size: 10
})

const searchForm = reactive({
  plan_id: '',
  status: ''
})

const workspaceName = ref('')
const managers = ref([])
const managerNames = computed(() => managers.value.map(m => m.nickname).join('、'))
const deleteTaskDialogVisible = ref(false)
const deleteTaskData = ref(null)
const jobDialogVisible = ref(false)
const jobDialogTask = ref(null)

// 从 jobs 数组实时统计各状态数量，避免依赖可能过时的数据库汇总字段
const jobCompletedCount = computed(() =>
  (jobDialogTask.value?.jobs || []).filter(j => j.status === 'completed').length
)
const jobFailedCount = computed(() =>
  (jobDialogTask.value?.jobs || []).filter(j => j.status === 'failed').length
)
const jobAbortedCount = computed(() =>
  (jobDialogTask.value?.jobs || []).filter(j => j.status === 'aborted').length
)
const jobRunningCount = computed(() =>
  (jobDialogTask.value?.jobs || []).filter(j => j.status === 'running').length
)
const jobPendingCount = computed(() =>
  (jobDialogTask.value?.jobs || []).filter(j => j.status === 'pending').length
)

const fetchWorkspaceDetail = async () => {
  try {
    const id = props.workspaceId || route.params.id
    if (!id) return
    const res = await getWorkspaceDetail({ workspace_id: parseInt(id) })
    if (res.code === 0) {
      workspaceName.value = res.data.workspace_name
      managers.value = res.data.manager || []
    }
  } catch (error) {
    console.error('获取工作空间详情失败:', error)
  }
}

const getStatusType = (status) => {
  const types = {
    'pending': 'info',
    'running': 'primary',
    'completed': 'success',
    'failed': 'danger',
    'aborted': 'warning'
  }
  return types[status] || 'info'
}

const getJobStatusType = (status) => {
  const types = {
    'pending': 'info',
    'running': 'primary',
    'completed': 'success',
    'failed': 'danger',
    'aborted': 'warning'
  }
  return types[status] || 'info'
}

const getJobBadgeColor = (status) => {
  const colors = {
    'pending': '#909399',
    'running': '#409eff',
    'completed': '#67c23a',
    'failed': '#f56c6c',
    'aborted': '#e6a23c'
  }
  return colors[status] || '#909399'
}

const getStatusText = (status) => {
  const texts = {
    'pending': '等待中',
    'running': '执行中',
    'completed': '已完成',
    'failed': '失败',
    'aborted': '已放弃'
  }
  return texts[status] || status
}

const getProgressStatus = (status) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  if (status === 'aborted') return 'warning'
  return ''
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const params = {
      workspace_id: filterWorkspaceId.value || props.id || 1,
      page_num: pagination.page_num,
      page_size: pagination.page_size
    }

    if (searchForm.plan_id) {
      params.plan_id = searchForm.plan_id
    }

    if (searchForm.status) {
      params.status = searchForm.status
    }

    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }

    const res = await axios.post('/api/v1/testtask/list', params)
    if (res.code === 0) {
      taskList.value = res.data.list
      total.value = res.data.total
    }
  } catch (e) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const refreshTasks = () => {
  fetchTasks()
}

const resetSearch = () => {
  searchKeyword.value = ''
  searchForm.plan_id = ''
  searchForm.status = ''
  pagination.page_num = 1
  fetchTasks()
}

const fetchPlanOptions = async () => {
  try {
    const params = {
      workspace_id: filterWorkspaceId.value || props.id || 1
    }
    const res = await axios.get('/api/v1/testplan/list', params)
    if (res.code === 0) {
      planOptions.value = res.data.list.map(p => ({
        plan_id: p.plan_id,
        name: p.name
      }))
    }
  } catch (e) {
    console.error('获取测试计划列表失败:', e)
  }
}

const handleSizeChange = (size) => {
  pagination.page_size = size
  pagination.page_num = 1
  fetchTasks()
}

const handlePageChange = (page) => {
  pagination.page_num = page
  fetchTasks()
}

const handleAbortTask = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要放弃任务"${row.task_name}"吗？这将终止所有正在运行的Job。`,
      '确认放弃',
      {
        confirmButtonText: '确定放弃',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await abortTestTask(row.task_id)
    if (res.code === 0) {
      ElMessage.success('任务已放弃')
      fetchTasks()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleDeleteTask = async (row) => {
  deleteTaskData.value = row
  deleteTaskDialogVisible.value = true
}

const confirmDeleteTask = async () => {
  if (!deleteTaskData.value) return
  try {
    const res = await deleteTestTask(deleteTaskData.value.task_id)
    if (res.code === 0) {
      ElMessage.success('任务已删除')
      deleteTaskDialogVisible.value = false
      deleteTaskData.value = null
      fetchTasks()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const showJobDetail = (row) => {
  jobDialogTask.value = row
  jobDialogVisible.value = true
}

const monitorJob = (row) => {
  router.push(`/testjobs/${row.job_id}/monitor`)
}

onBeforeMount(() => {
  if (route.query.plan_id) {
    searchForm.plan_id = Number(route.query.plan_id)
    if (route.query.plan_name) {
      planOptions.value.push({
        plan_id: Number(route.query.plan_id),
        name: route.query.plan_name
      })
    }
  }
  if (props.workspaceId) {
    filterWorkspaceId.value = props.workspaceId
  } else if (route.query.workspace_id) {
    filterWorkspaceId.value = route.query.workspace_id
  }
})

onMounted(() => {
  fetchWorkspaceDetail()
  fetchPlanOptions()
  fetchTasks()
})
</script>

<style scoped>
.testtask-management {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f5f5f5;
  padding-bottom: 10px;
}

.scroll-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ttl-header-card { background: #fff; border-radius: 12px; }
.ttl-header-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; }
.ttl-title-group { display: flex; align-items: center; gap: 12px; }
.ttl-icon-wrap { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ttl-title { margin: 0; font-size: 17px; font-weight: 700; color: #1d1d1f; }
.ttl-subtitle { margin: 2px 0 0; font-size: 12px; color: #8e8e93; }
.ttl-header-actions { display: flex; gap: 8px; }

.header-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.info-text {
  margin: 0;
  font-size: 12px;
  color: #646a73;
}

.info-text .font-medium {
  font-weight: 500;
  color: #303133;
}

.manager-tag {
  background: #dbeafe;
  color: #2563eb;
  border: none;
}


.search-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #fff;
  border-radius: 12px;
}

.search-input {
  width: 200px;
}

.search-select {
  width: 140px;
}

.search-btn,
.reset-btn {
  background: #f5f7fa;
  border: 1px solid #e4e8ec;
  color: #646a73;
}

.search-btn:hover,
.reset-btn:hover {
  background: #e8eef3;
}

.action-group {
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
  justify-content: center;
}

.action-btn {
  border: none;
  border-radius: 6px;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.12s ease;
  font-weight: 500;
}

.action-run { background: #fffbeb; color: #d97706; }
.action-run:hover { background: #fef3c7; }
.action-view { background: #eef2ff; color: #5b6ef7; }
.action-view:hover { background: #e0e7ff; }
.action-delete { background: #fef2f2; color: #dc2626; }
.action-delete:hover { background: #fee2e2; }

.table-container {
  flex: 1;
  min-height: 0;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  overflow: hidden;
}

.id-text {
  color: #409eff;
  font-weight: 600;
}

.progress-text {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: block;
  text-align: center;
}

.job-stats {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.duration-text {
  color: #606266;
}

.jd-dialog {
  --jd-radius: 16px;
}

.jd-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px 16px;
}

.jd-dialog-header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.jd-dialog-header-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  color: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.jd-dialog-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  line-height: 1.3;
}

.jd-dialog-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #8e8e93;
}

.jd-dialog-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.jd-summary-stats {
  display: flex;
  gap: 10px;
  background: #f8f9fa;
  padding: 6px 12px;
  border-radius: 8px;
}

.jd-stat {
  font-size: 11px;
  font-weight: 500;
}

.jd-stat-success { color: #67c23a; }
.jd-stat-running { color: #409eff; }
.jd-stat-danger { color: #f56c6c; }
.jd-stat-warning { color: #e6a23c; }
.jd-stat-info { color: #909399; }

.jd-close-btn {
  --el-bg-color: #f5f5f5;
  color: #8e8e93;
}

.jd-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 24px 20px;
}

.jd-card {
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s ease;
  position: relative;
}

.jd-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
}

.jd-card--pending::before { background: #909399; }
.jd-card--running::before { background: #409eff; }
.jd-card--completed::before { background: #67c23a; }
.jd-card--failed::before { background: #f56c6c; }
.jd-card--aborted::before { background: #e6a23c; }

.jd-card-inner {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  margin-left: 4px;
  padding: 0;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.jd-card:hover .jd-card-inner {
  border-color: #d0d5e0;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}

.jd-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px 10px;
}

.jd-card-top-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.jd-card-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.jd-card-name {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jd-card-top-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.jd-card-status-tag {
  font-weight: 500;
}

.jd-card-btn {
  --el-button-size: 28px;
}

.jd-card-divider {
  height: 1px;
  background: #f0f2f5;
  margin: 0 14px;
}

.jd-card-bottom {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
  font-size: 12px;
  color: #8e8e93;
  padding: 8px 14px 10px;
}

.jd-meta {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #6b7280;
}

.jd-meta span {
  white-space: nowrap;
}

.jd-empty {
  padding: 48px 24px;
  text-align: center;
  color: #c0c4cc;
}

.jd-empty p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #909399;
}

.ttl-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }
</style>

<style>
/* 任务详情弹窗：固定高度 + 滚动。
   由于 Element Plus 的 dialog 组件不受 Vue scoped :deep() 穿透，
   故使用非 scoped 全局样式。 */
.jd-dialog .el-dialog__body {
  padding: 0;
  max-height: calc(80vh - 100px);
  overflow-y: auto;
}
</style>




