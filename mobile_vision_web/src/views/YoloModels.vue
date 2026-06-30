<template>
  <div class="yolo-models">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <el-card class="header-card rounded-xl shadow-md border-0 overflow-hidden bg-white">
      <div class="relative overflow-hidden">
        <div class="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-blue-100 to-purple-100 rounded-full -mr-24 -mt-24 opacity-70"></div>
        <div class="absolute bottom-0 left-0 w-36 h-36 bg-gradient-to-tr from-green-100 to-blue-100 rounded-full -ml-18 -mb-18 opacity-70"></div>
        <div class="relative flex flex-col md:flex-row justify-between items-start md:items-center p-4 z-10">
          <div class="page-header mb-3 md:mb-0">
            <h1 class="text-xl font-bold text-gray-800 mb-1">模型管理</h1>
            <p class="text-sm text-gray-600">管理YOLO目标检测训练模型</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <el-button type="success" @click="loadModels()" class="text-sm px-4">
              <el-icon class="mr-1" :size="14"><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <el-card class="filter-card rounded-xl shadow-md border-0 bg-white">
      <div class="flex flex-wrap items-center gap-4 p-4">
        <el-input v-model="searchKeyword" placeholder="搜索模型名称" class="w-44" size="default" @keyup.enter="handleSearch">
          <template #prefix><el-icon :size="14"><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="handleSearch">
          <el-icon :size="14"><Search /></el-icon> 查询
        </el-button>
      </div>
    </el-card>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
    <el-card class="table-card rounded-xl shadow-md border-0 bg-white">
      <div class="table-container">
        <el-table
          :data="models"
          v-loading="loading"
          element-loading-text="加载中..."
          style="width: 100%"
          :cell-style="{ textAlign: 'center' }"
          :header-cell-style="{ textAlign: 'center', backgroundColor: '#f5f7fa', color: '#606266' }"
          border
          empty-text="暂无训练好的模型"
          :height="tableHeight"
        >
        <el-table-column prop="id" label="模型ID" width="120">
          <template #default="{ row }">
            <span class="id-text">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.name" placement="top">
              <span class="model-name-text">{{ row.name }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="dataset_id" label="数据集ID" width="120">
          <template #default="{ row }">
            <span class="id-text">#{{ row.dataset_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dataset_name" label="数据集名称" width="200">
          <template #default="{ row }">
            <span>{{ row.dataset_name || '未知数据集' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">
            <span class="size-text">{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="指标" min-width="280">
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
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="info" size="small" @click="showModelDetail(row)">详情</el-button>
              <el-button type="primary" size="small" @click="openTestModelDialog(row)">测试</el-button>
              <el-button type="danger" size="small" @click="removeModel(row.id)">删除</el-button>
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
        @size-change="(size) => { pagination.pageSize = size; loadModels(1) }"
        @current-change="handlePageChange"
        background
      />
    </div>
    </div>

    <el-dialog v-model="showTestModelDialog" title="测试模型" width="600px">
      <el-form :model="testForm" label-width="100px">
        <el-form-item label="选择图片">
          <el-upload
            ref="testUploadRef"
            :auto-upload="false"
            :file-list="testFiles"
            :on-change="handleTestFileChange"
            :on-remove="handleTestFileRemove"
            accept="image/*"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
          </el-upload>
        </el-form-item>
        <el-form-item label="置信度阈值">
          <el-slider v-model="confidenceThreshold" :min="0" :max="1" :step="0.05" />
        </el-form-item>
      </el-form>

      <div v-if="testResults" class="test-results">
        <h4>检测结果:</h4>
        <div class="result-image">
          <img 
            v-if="testImageUrl" 
            :src="testImageUrl" 
            alt="检测结果" 
            class="clickable-image"
            @click="showImagePreview = true"
          />
          <p class="image-hint">点击图片放大查看</p>
        </div>
        <div class="result-list">
          <el-alert
            v-for="(result, index) in testResults.predictions"
            :key="index"
            :title="`${result.class_name} - 置信度: ${(result.confidence * 100).toFixed(1)}%`"
            type="info"
            show-icon
          />
        </div>
      </div>

      <div v-if="showImagePreview" class="image-preview-overlay" @click="closePreview">
        <div class="preview-container" @click.stop>
          <button class="close-btn" @click="closePreview">×</button>
          <div class="preview-controls">
            <button class="control-btn reset-btn" @click="resetView">↺</button>
            <span class="scale-info">{{ Math.round(scale * 100) }}%</span>
          </div>
          <div 
            class="image-wrapper"
            @wheel="handleWheel"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
            @dblclick="handleDoubleClick"
          >
            <img 
              ref="imageRef"
              :src="testImageUrl" 
              alt="放大预览" 
              class="preview-image"
              :style="{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                cursor: scale > 1 ? 'grab' : 'default'
              }"
            />
          </div>
          <div class="preview-hint">
            <p>滚轮缩放 | 拖拽移动（放大后）</p>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showTestModelDialog = false">取消</el-button>
        <el-button type="primary" @click="testModel" :loading="testing">测试</el-button>
      </template>
    </el-dialog>

    <el-drawer
      title="模型详情"
      v-model="drawerVisible"
      direction="rtl"
      size="500px"
      :with-header="true"
    >
      <div v-if="currentModel" class="model-detail">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row">
            <span class="label">模型ID:</span>
            <span class="value">#{{ currentModel.id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">模型名称:</span>
            <span class="value">{{ currentModel.name }}</span>
          </div>
          <div class="detail-row">
            <span class="label">模型大小:</span>
            <span class="value">{{ formatFileSize(currentModel.size) }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>数据集信息</h3>
          <div class="detail-row">
            <span class="label">数据集ID:</span>
            <span class="value">#{{ currentModel.dataset_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">数据集名称:</span>
            <span class="value">{{ currentModel.dataset_name || '未知数据集' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">图片数量:</span>
            <span class="value">{{ currentModel.dataset_detail?.image_count || 0 }} 张</span>
          </div>
          <div class="detail-row">
            <span class="label">标注实例:</span>
            <span class="value">{{ currentModel.dataset_detail?.label_count || 0 }} 个</span>
          </div>
          <div class="detail-row">
            <span class="label">类别数量:</span>
            <span class="value">{{ currentModel.dataset_detail?.class_count || 0 }} 类</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>训练参数</h3>
          <div class="detail-row">
            <span class="label">基础模型:</span>
            <span class="value">{{ currentModel.config?.model_name || currentModel.model_name || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">训练轮数:</span>
            <span class="value">{{ currentModel.config?.epochs || '-' }} epochs</span>
          </div>
          <div class="detail-row">
            <span class="label">批次大小:</span>
            <span class="value">{{ currentModel.config?.batch_size || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">图片尺寸:</span>
            <span class="value">{{ currentModel.config?.imgsz || '-' }} px</span>
          </div>
          <div class="detail-row">
            <span class="label">训练设备:</span>
            <span class="value">{{ currentModel.config?.device || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">学习率:</span>
            <span class="value">{{ currentModel.config?.lr0 || '-' }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>类别信息</h3>
          <div v-if="currentModel.classes && currentModel.classes.length > 0" class="classes-content">
            <div v-for="(cls, index) in currentModel.classes" :key="index" class="class-item">
              <span class="class-index">{{ index + 1 }}.</span>
              <span class="class-name">{{ cls }}</span>
            </div>
          </div>
          <div v-else class="no-data">暂无类别信息</div>
        </div>

        <div class="detail-section">
          <h3>其他信息</h3>
          <div class="detail-row">
            <span class="label">任务ID:</span>
            <span class="value">#{{ currentModel.task_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">模型路径:</span>
            <span class="value path-value">{{ currentModel.path }}</span>
          </div>
          <div class="detail-row">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatTime(currentModel.created_at) }}</span>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog
      v-model="showDeleteModelDialog"
      title="删除模型"
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
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除模型吗？</h3>
        <p class="text-gray-600 mb-2">模型名称：<em><strong>{{ deleteModelInfo.name }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">删除后模型文件将被永久删除且无法恢复，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteModelDialog = false"
                     class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">
            取消
          </el-button>
          <el-button type="danger" @click="confirmDeleteModel"
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
import { Refresh, UploadFilled, Warning, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getModelsList, deleteModel as deleteModelApi, predictImage } from '@/network/api'

const models = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const currentModel = ref(null)
const showDeleteModelDialog = ref(false)
const deleteModelInfo = ref({ id: null, name: '' })
const searchKeyword = ref('')

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const showTestModelDialog = ref(false)
const testForm = ref({})
const testFiles = ref([])
const currentTestModel = ref(null)
const confidenceThreshold = ref(0.25)
const testResults = ref(null)
const testImageUrl = ref('')
const testing = ref(false)
const showImagePreview = ref(false)
const scale = ref(1)
const position = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const imageRef = ref(null)

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

const loadModels = async (page = pagination.value.page) => {
  loading.value = true
  try {
    const params = { page, page_size: pagination.value.pageSize }
    if (searchKeyword.value?.trim()) {
      params.keyword = searchKeyword.value.trim()
    }
    const resp = await getModelsList(params)
    if (resp.code === 0) {
      models.value = resp.data.models || []
      pagination.value.total = resp.data.total || 0
      pagination.value.page = resp.data.page || 1
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadModels(page)
}

const handleSearch = () => {
  pagination.value.page = 1
  loadModels(1)
}

const removeModel = (id) => {
  const model = models.value.find(m => m.id === id)
  deleteModelInfo.value = {
    id: id,
    name: model ? model.name : '未知模型'
  }
  showDeleteModelDialog.value = true
}

const confirmDeleteModel = async () => {
  try {
    const resp = await deleteModelApi(deleteModelInfo.value.id)
    if (resp.code === 0) {
      ElMessage.success('删除成功')
      showDeleteModelDialog.value = false
      loadModels()
    } else {
      ElMessage.error(resp.message || '删除失败')
    }
  } catch (error) {
    console.error('删除模型失败:', error)
    ElMessage.error('删除失败：网络或服务器错误')
  }
}

const showModelDetail = (model) => {
  currentModel.value = model
  drawerVisible.value = true
}

const openTestModelDialog = (model) => {
  currentTestModel.value = model
  testFiles.value = []
  testResults.value = null
  testImageUrl.value = ''
  confidenceThreshold.value = 0.25
  showTestModelDialog.value = true
}

const handleTestFileChange = (file, fileList) => {
  testFiles.value = fileList
}

const handleTestFileRemove = (file, fileList) => {
  testFiles.value = fileList
}

const testModel = async () => {
  if (testFiles.value.length === 0) {
    ElMessage.warning('请选择要测试的图片')
    return
  }

  testing.value = true
  try {
    const file = testFiles.value[0].raw
    const resp = await predictImage(currentTestModel.value.id, file, {
      conf_threshold: confidenceThreshold.value,
      save_result: true
    })
    if (resp.code === 0) {
      testResults.value = resp.data
      testImageUrl.value = resp.data.result_image || ''
      if (testImageUrl.value && !testImageUrl.value.startsWith('http')) {
        testImageUrl.value = `${import.meta.env.VITE_APP_SERVER_URL}${testImageUrl.value}`
      }
      ElMessage.success('测试完成')
    } else {
      ElMessage.error(resp.message || '测试失败')
    }
  } catch (error) {
    console.error('测试模型失败:', error)
    ElMessage.error('测试失败：网络或服务器错误')
  } finally {
    testing.value = false
  }
}

const handleWheel = (e) => {
  e.preventDefault()
  const rect = e.currentTarget.getBoundingClientRect()
  const mouseX = e.clientX - rect.left - rect.width / 2
  const mouseY = e.clientY - rect.top - rect.height / 2
  
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(1, Math.min(10, scale.value + delta))
  
  const scaleRatio = newScale / scale.value
  position.value = {
    x: mouseX * (1 - scaleRatio) + position.value.x * scaleRatio,
    y: mouseY * (1 - scaleRatio) + position.value.y * scaleRatio
  }
  
  scale.value = newScale
}

const handleDoubleClick = (e) => {
  if (scale.value <= 1) {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - rect.width / 2
    const mouseY = e.clientY - rect.top - rect.height / 2
    
    const targetScale = 3.5
    const scaleRatio = targetScale / scale.value
    position.value = {
      x: mouseX * (1 - scaleRatio) + position.value.x * scaleRatio,
      y: mouseY * (1 - scaleRatio) + position.value.y * scaleRatio
    }
    
    scale.value = targetScale
  } else {
    resetView()
  }
}

const handleMouseDown = (e) => {
  if (scale.value <= 1) return
  e.preventDefault()
  isDragging.value = true
  dragStart.value = { x: e.clientX - position.value.x, y: e.clientY - position.value.y }
}

const handleMouseMove = (e) => {
  if (!isDragging.value) return
  e.preventDefault()
  position.value = {
    x: e.clientX - dragStart.value.x,
    y: e.clientY - dragStart.value.y
  }
}

const handleMouseUp = () => {
  isDragging.value = false
}

const resetView = () => {
  scale.value = 1
  position.value = { x: 0, y: 0 }
}

const closePreview = () => {
  showImagePreview.value = false
  scale.value = 1
  position.value = { x: 0, y: 0 }
  isDragging.value = false
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

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
}

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.yolo-models {
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

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.action-buttons .el-button {
  padding: 6px 12px;
}

.table-container {
  padding: 20px;
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

.time-text {
  font-size: 12px;
  color: #606266;
}

.size-text {
  font-size: 12px;
  color: #606266;
}

.model-name-text {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  cursor: pointer;
}

.model-name-text:hover {
  color: #409eff;
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

.classes-content {
  max-height: 150px;
  overflow-y: auto;
}

.class-item {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.class-item:last-child {
  border-bottom: none;
}

.class-index {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
  width: 24px;
}

.class-name {
  font-size: 12px;
  color: #606266;
}

.test-results {
  margin-top: 20px;
}

.result-image {
  text-align: center;
  margin: 10px 0;
}

.result-image img {
  max-width: 100%;
  max-height: 400px;
  border: 1px solid #ddd;
}

.result-list {
  margin-top: 10px;
}

.clickable-image {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.clickable-image:hover {
  transform: scale(1.02);
}

.image-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.image-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  cursor: pointer;
}

.preview-container {
  position: relative;
  width: 90vw;
  height: 90vh;
  display: flex;
  flex-direction: column;
  cursor: default;
}

.preview-controls {
  position: absolute;
  top: 10px;
  right: 60px;
  display: flex;
  gap: 10px;
  align-items: center;
  z-index: 10;
}

.control-btn {
  width: 36px;
  height: 36px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 20px;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s ease;
  position: relative;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.control-btn:hover {
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 36px;
  height: 36px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 20px;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.close-btn:hover {
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
}

.scale-info {
  color: white;
  font-size: 14px;
  background-color: rgba(255, 255, 255, 0.2);
  padding: 6px 12px;
  border-radius: 4px;
}

.image-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: transform 0.1s ease-out;
}

.preview-hint {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.model-detail {
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
}

.detail-row .value.path-value {
  font-family: monospace;
  font-size: 11px;
  word-break: break-all;
  overflow-wrap: break-word;
  text-align: left;
  line-height: 1.4;
}

.detail-row .label {
  width: 100px;
  flex-shrink: 0;
}

.detail-row .value {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.no-data {
  color: #c0c4cc;
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