<template>
  <div class="yolo-training">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <!-- 页面标题卡片 -->
      <el-card
        class="header-card rounded-xl shadow-md border-0 overflow-hidden bg-white"
      >
        <div class="relative overflow-hidden">
          <div class="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-blue-100 to-purple-100 rounded-full -mr-24 -mt-24 opacity-70"></div>
          <div class="absolute bottom-0 left-0 w-36 h-36 bg-gradient-to-tr from-green-100 to-blue-100 rounded-full -ml-18 -mb-18 opacity-70"></div>

          <div class="relative flex flex-col md:flex-row justify-between items-start md:items-center p-4 z-10">
            <div class="page-header mb-3 md:mb-0">
              <h1 class="text-xl font-bold text-gray-800 mb-1">训练任务管理</h1>
              <p class="text-sm text-gray-600">管理YOLO目标检测模型训练任务</p>
            </div>

            <div class="flex flex-wrap gap-2">
              <el-button
                type="success"
                @click="loadTasks()"
                class="text-sm px-4"
              >
                <el-icon class="mr-1" :size="14">
                  <Refresh/>
                </el-icon>
                刷新
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 筛选区域卡片 -->
      <el-card class="filter-card rounded-xl shadow-md border-0 bg-white">
        <div class="flex flex-wrap items-center gap-4 p-4">
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600">任务状态:</label>
            <el-select
              v-model="filterStatus"
              placeholder="全部"
              class="w-36"
              size="default"
            >
              <el-option label="全部" :value="''" />
              <el-option label="等待中" :value="'pending'" />
              <el-option label="训练中" :value="'running'" />
              <el-option label="已完成" :value="'completed'" />
              <el-option label="失败" :value="'failed'" />
            </el-select>
          </div>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索数据集名称"
            class="w-44"
            size="default"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon :size="14"><Search/></el-icon>
            </template>
          </el-input>
          <el-button
            type="primary"
            @click="handleSearch"
          >
            <el-icon :size="14"><Search/></el-icon> 查询
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
      <!-- 任务列表卡片 -->
      <el-card class="table-card rounded-xl shadow-md border-0 bg-white overflow-hidden">
        <div class="table-container">
          <el-table
            :data="tasks"
            v-loading="loading"
            element-loading-text="加载中..."
            style="width: 100%"
            :cell-style="{ textAlign: 'center' }"
            :header-cell-style="{ textAlign: 'center', backgroundColor: '#f5f7fa', color: '#606266' }"
            border
            empty-text="暂无训练任务"
            :height="tableHeight"
          >
            <el-table-column prop="id" label="任务ID" width="120">
              <template #default="{ row }">
                <span class="id-text">#{{ row.id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="dataset_name" label="数据集名称" width="220">
              <template #default="{ row }">
                <span>{{ row.dataset_name || '未知数据集' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" effect="dark">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="180">
              <template #default="{ row }">
                <el-progress
                  :percentage="Math.floor(row.progress)"
                  :stroke-width="10"
                  :show-text="true"
                  :color="getProgressColor(row.status)"
                />
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="180">
              <template #default="{ row }">
                <span class="time-text">{{ formatTime(row.start_time) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="结束时间" width="180">
              <template #default="{ row }">
                <span class="time-text">{{ formatTime(row.end_time) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="指标" min-width="220">
              <template #default="{ row }">
                <div v-if="row.metrics" class="metrics-grid">
                  <span v-if="row.metrics.map50 !== undefined && row.metrics.map50 !== null" class="metric-badge map50">mAP50: {{ (row.metrics.map50 * 100).toFixed(1) }}%</span>
                  <span v-if="row.metrics['map50-95'] !== undefined && row.metrics['map50-95'] !== null" class="metric-badge map50-95">mAP50-95: {{ (row.metrics['map50-95'] * 100).toFixed(1) }}%</span>
                  <span v-if="row.metrics.precision !== undefined && row.metrics.precision !== null" class="metric-badge precision">Precision: {{ (row.metrics.precision * 100).toFixed(1) }}%</span>
                  <span v-if="row.metrics.recall !== undefined && row.metrics.recall !== null" class="metric-badge recall">Recall: {{ (row.metrics.recall * 100).toFixed(1) }}%</span>
                </div>
                <span v-else class="no-data">-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button type="info" size="small" @click="showTaskDetail(row)">详情</el-button>
                  <el-button
                    v-if="row.status === 'pending' || row.status === 'running'"
                    type="warning"
                    size="small"
                    @click="abortTask(row)"
                  >放弃</el-button>
                  <el-button type="danger" size="small" @click="deleteTask(row.id)">删除</el-button>
                  <span class="btn-placeholder">
                    <el-button
                      v-if="row.status === 'failed'"
                      type="primary"
                      size="small"
                      @click="retryTask(row.id)"
                      icon="Refresh"
                    >重试</el-button>
                  </span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <div class="table-footer">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="(size) => { pagination.pageSize = size; loadTasks(1) }"
          @current-change="handlePageChange"
          background
        />
      </div>
    </div>

    <el-drawer
      title="任务详情"
      v-model="drawerVisible"
      direction="rtl"
      size="500px"
      :with-header="true"
    >
      <div v-if="currentTask" class="task-detail">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row">
            <span class="label">任务ID:</span>
            <span class="value">#{{ currentTask.id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">状态:</span>
            <span class="value">
              <el-tag :type="getStatusType(currentTask.status)" effect="dark">
                {{ getStatusText(currentTask.status) }}
              </el-tag>
            </span>
          </div>
        </div>

        <div class="detail-section">
          <h3>数据集信息</h3>
          <div class="detail-row">
            <span class="label">数据集ID:</span>
            <span class="value">#{{ currentTask.dataset_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">数据集名称:</span>
            <span class="value">{{ currentTask.dataset_name || '未知数据集' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">图片数量:</span>
            <span class="value">{{ currentTask.dataset_detail?.image_count || 0 }} 张</span>
          </div>
          <div class="detail-row">
            <span class="label">标注实例:</span>
            <span class="value">{{ currentTask.dataset_detail?.label_count || 0 }} 个</span>
          </div>
          <div class="detail-row">
            <span class="label">类别数量:</span>
            <span class="value">{{ currentTask.dataset_detail?.class_count || 0 }} 类</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>训练参数</h3>
          <div class="detail-row">
            <span class="label">基础模型:</span>
            <span class="value">{{ currentTask.config?.model_name || currentTask.model_name }}</span>
          </div>
          <div class="detail-row">
            <span class="label">训练轮数:</span>
            <span class="value">{{ currentTask.config?.epochs || currentTask.total_epochs || 0 }} epochs</span>
          </div>
          <div class="detail-row">
            <span class="label">批次大小:</span>
            <span class="value">{{ currentTask.config?.batch_size || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">图片尺寸:</span>
            <span class="value">{{ currentTask.config?.imgsz || '-' }} px</span>
          </div>
          <div class="detail-row">
            <span class="label">训练设备:</span>
            <span class="value">{{ currentTask.config?.device || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">学习率:</span>
            <span class="value">{{ currentTask.config?.lr0 || '-' }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>时间信息</h3>
          <div class="detail-row">
            <span class="label">开始时间:</span>
            <span class="value">{{ formatTime(currentTask.start_time) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">结束时间:</span>
            <span class="value">{{ formatTime(currentTask.end_time) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatTime(currentTask.created_at) }}</span>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog
      v-model="showDeleteTaskDialog"
      title="删除训练任务"
      width="420px"
      class="delete-dialog rounded-xl overflow-hidden"
      :close-on-click-modal="false"
    >
      <div class="text-center py-8">
        <div
          class="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <el-icon :size="32" class="text-red-500">
            <Warning/>
          </el-icon>
        </div>
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除训练任务吗？</h3>
        <p class="text-gray-600 mb-2">任务ID：<em><strong>#{{ deleteTaskInfo.id }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">此操作不可撤销，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteTaskDialog = false"
                     class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">
            取消
          </el-button>
          <el-button type="danger" @click="confirmDeleteTask"
                     class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-sm py-1.5 px-4 rounded-lg">
            确定删除
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Refresh, Warning, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteTrainTask, getTrainTasks, retryTrainTask, abortTrainTask } from '@/network/api.js'

const tasks = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const currentTask = ref(null)
const showDeleteTaskDialog = ref(false)
const deleteTaskInfo = ref({ id: null })
const filterStatus = ref('')
const searchKeyword = ref('')

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

const loadTasks = async (page = pagination.value.page) => {
  loading.value = true
  try {
    const params = { page, page_size: pagination.value.pageSize }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (searchKeyword.value?.trim()) {
      params.keyword = searchKeyword.value.trim()
    }
    const resp = await getTrainTasks(params)
    if (resp.code === 0) {
      tasks.value = resp.data.tasks || []
      pagination.value.total = resp.data.total || 0
      pagination.value.page = resp.data.page || 1
    }
  } catch (error) {
    console.error('加载训练任务失败:', error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadTasks(page)
}

const handleSearch = () => {
  pagination.value.page = 1
  loadTasks(1)
}

const abortTask = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要放弃任务"${row.dataset_name}"吗？`,
      '确认放弃',
      {
        confirmButtonText: '确定放弃',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const resp = await abortTrainTask(row.id)
    if (resp.code === 0) {
      ElMessage.success('任务已放弃')
      loadTasks()
    } else {
      ElMessage.error(resp.message || '操作失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const deleteTask = (id) => {
  deleteTaskInfo.value = { id: id }
  showDeleteTaskDialog.value = true
}

const confirmDeleteTask = async () => {
  try {
    const resp = await deleteTrainTask(deleteTaskInfo.value.id)
    if (resp.code === 0) {
      ElMessage.success('删除成功')
      showDeleteTaskDialog.value = false
      loadTasks()
    } else {
      ElMessage.error(resp.message || '删除失败')
    }
  } catch (error) {
    console.error('删除任务失败:', error)
    ElMessage.error('删除失败：网络或服务器错误')
  }
}

const retryTask = async (id) => {
  try {
    const resp = await retryTrainTask(id)
    if (resp.code === 0) {
      ElMessage.success('重试任务已提交')
      loadTasks()
    } else {
      ElMessage.error(resp.message || '重试失败')
    }
  } catch (error) {
    console.error('重试任务失败:', error)
    ElMessage.error('重试失败：网络或服务器错误')
  }
}

const showTaskDetail = (task) => {
  currentTask.value = task
  drawerVisible.value = true
}

const getStatusType = (status) => {
  const statusMap = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'aborted': 'warning'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'pending': '等待中',
    'running': '训练中',
    'completed': '已完成',
    'failed': '失败',
    'aborted': '已放弃'
  }
  return textMap[status] || status
}

const getProgressColor = (status) => {
  const colorMap = {
    'pending': '#909399',
    'running': '#409eff',
    'completed': '#67c23a',
    'failed': '#f56c6c',
    'aborted': '#e6a23c'
  }
  return colorMap[status] || '#409eff'
}

const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.yolo-training {
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
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding-top: 10px;
}

.header-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

.filter-card {
  background: white;
}

.table-card {
  background: white;
}

.page-header {
  z-index: 10;
}

.page-header h1 {
  margin: 0;
}

.page-header p {
  margin: 4px 0 0;
}

.table-container {
  padding: 16px;
}

.table-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px 20px;
  margin-top: 10px;
  background-color: white;
  border-top: 1px solid #ebeef5;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  z-index: 100;
}

.id-text {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  min-height: 32px;
  align-items: center;
}

.action-buttons .btn-placeholder {
  display: inline-flex;
}

.time-text {
  font-size: 12px;
  color: #606266;
}

.metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.metric-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}

.metric-badge.map50 {
  background-color: #e8f4fd;
  color: #1890ff;
}

.metric-badge.map50-95 {
  background-color: #f0f5ff;
  color: #722ed1;
}

.metric-badge.precision {
  background-color: #f6ffed;
  color: #52c41a;
}

.metric-badge.recall {
  background-color: #fff7e6;
  color: #fa8c16;
}

.no-data {
  color: #c0c4cc;
}

.task-detail {
  padding: 10px 0;
}

.detail-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.detail-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.detail-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row .label {
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
  width: 100px;
}

.detail-row .value {
  font-size: 13px;
  color: #606266;
  flex: 1;
  text-align: right;
  min-width: 0;
  word-break: break-word;
}

.delete-dialog {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);

  .el-dialog__header {
    padding: 1.5rem;
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
  }

  .el-dialog__title {
    font-size: 1.125rem;
    font-weight: 600;
    color: #1a202c;
  }

  .el-dialog__body {
    padding: 0;
  }

  .el-dialog__footer {
    padding: 0;
    background-color: transparent;
  }
}
</style>
