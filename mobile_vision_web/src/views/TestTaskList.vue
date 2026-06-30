<template>
  <div class="testtask-management">
    <div class="sticky-header">
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">测试任务管理</h1>
          <p class="page-subtitle">管理工作空间下的测试任务</p>
        </div>
        <div class="header-right">
          <div class="header-info">
            <p class="info-text">当前空间：<span class="font-medium">{{ workspaceName }}</span></p>
            <el-tag
              v-for="manager in managers"
              :key="manager.username"
              size="small"
              class="manager-tag"
            >
              <el-icon class="mr-1" :size="12"><User/></el-icon>
              管理员：{{ manager.nickname }}
            </el-tag>
          </div>
          <el-button type="primary" @click="refreshTasks" class="refresh-button">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
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
        :header-cell-style="{ textAlign: 'center', backgroundColor: '#f5f7fa', color: '#606266' }"
        border
        empty-text="暂无测试任务"
        row-key="task_id"
        :height="tableHeight"
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
                <el-table-column prop="duration" label="用时(秒)" width="80">
                  <template #default="{ row }">{{ row.duration || '-' }}</template>
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
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
                  v-if="row.status === 'running' || row.status === 'pending'"
                  type="danger"
                  size="small"
                  text
                  @click="handleAbortTask(row)"
                >
                  放弃
                </el-button>
                <el-button
                  v-if="row.status !== 'running'"
                  type="danger"
                  size="small"
                  text
                  @click="handleDeleteTask(row)"
                >
                  删除
                </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="pagination.page_num"
        v-model:page-size="pagination.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        background
      />
    </div>
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
import { Refresh, Search, User, Warning } from '@element-plus/icons-vue'
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
const deleteTaskDialogVisible = ref(false)
const deleteTaskData = ref(null)

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

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
  padding-top: 10px;
  overflow: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2d3d;
}

.page-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #646a73;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
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
  background: #ecf5ff;
  border-color: #d9ecff;
  color: #409eff;
}

.refresh-button {
  background: linear-gradient(135deg, #4080ff 0%, #366fc9 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 128, 255, 0.3);
}

.search-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 1rem;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
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

.table-container {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  padding: 1rem;
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

.table-footer {
  margin-top: 10px;
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px 20px;
  background-color: #ffffff;
  border-top: 1px solid #ebeef5;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  z-index: 100;
}
</style>
