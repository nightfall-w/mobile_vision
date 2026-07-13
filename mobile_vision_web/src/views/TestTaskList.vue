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
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row.jobs && row.jobs.length > 0" class="job-detail">
              <el-table :data="row.jobs" style="width: 100%" size="small">
                <el-table-column label="Job ID" width="80">
                  <template #default="{ row }">#{{ row.job_id }}</template>
                </el-table-column>
                <el-table-column prop="case_name" label="用例名称" min-width="150" show-overflow-tooltip />
                <el-table-column prop="device_name" label="设备" width="120" />
                <el-table-column prop="llm_name" label="LLM" min-width="130" show-overflow-tooltip />
                <el-table-column prop="yolo_name" label="YOLO模型" min-width="110" show-overflow-tooltip />
                <el-table-column prop="reasoning_effort" label="推理强度" width="100" />
                <el-table-column prop="ocr_engine" label="OCR" width="80" />
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getJobStatusType(row.status)" size="small">
                      {{ getStatusText(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="duration" label="用时" width="100">
                  <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
                </el-table-column>
                <el-table-column prop="start_time" label="开始时间" width="160" />
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button
                      type="primary"
                      size="small"
                      @click="monitorJob(row)"
                    >
                      监控
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else class="no-jobs">该任务暂无Job</div>
          </template>
        </el-table-column>
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
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
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
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeMount, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, User, Warning, List } from '@element-plus/icons-vue'
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
    'failed': 'danger'
  }
  return types[status] || 'info'
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

const monitorJob = (row) => {
  router.push(`/testjobs/${row.job_id}/monitor`)
}

onBeforeMount(() => {
  if (route.query.plan_id) {
    searchForm.plan_id = route.query.plan_id
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
  overflow: hidden;
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

.job-detail {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.no-jobs {
  padding: 20px;
  text-align: center;
  color: #909399;
}

.ttl-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }
</style>
