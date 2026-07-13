<template>
  <div class="yolo-training">
    <div class="sticky-header">
      <div class="yt-header-card">
        <div class="yt-header-inner">
          <div class="yt-title-group">
            <div class="yt-icon-wrap"><el-icon :size="18"><Aim /></el-icon></div>
            <div>
              <h1 class="yt-title">YOLO 训练中心</h1>
              <p class="yt-subtitle">训练任务管理与已训练模型管理</p>
            </div>
          </div>
          <div class="yt-header-actions">
            <button class="yt-btn yt-btn-ghost" @click="refreshCurrentTab">
              <el-icon :size="14"><Refresh /></el-icon> 刷新
            </button>
          </div>
        </div>
        <div class="yt-header-tabs">
          <div class="yt-tab-bar">
            <div class="yt-tab-item" :class="{ active: activeTab === 'training' }" @click="switchTab('training')">
              <el-icon><List /></el-icon>
              <span>训练任务</span>
            </div>
            <div class="yt-tab-item" :class="{ active: activeTab === 'models' }" @click="switchTab('models')">
              <el-icon><Aim /></el-icon>
              <span>已训练模型</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'training'" class="filter-card">
        <div class="filter-content">
          <div class="filter-group">
            <label class="filter-label">任务状态</label>
            <el-select v-model="filterStatus" placeholder="全部" class="filter-select">
              <el-option label="全部" :value="''" />
              <el-option label="等待中" :value="'pending'" />
              <el-option label="训练中" :value="'running'" />
              <el-option label="已完成" :value="'completed'" />
              <el-option label="失败" :value="'failed'" />
            </el-select>
          </div>
          <el-input v-model="searchKeyword" placeholder="搜索数据集名称" class="filter-input" @keyup.enter="handleSearch">
            <template #prefix><el-icon><Search/></el-icon></template>
          </el-input>
          <button class="filter-btn" @click="handleSearch">
            <el-icon :size="13"><Search/></el-icon> 查询
          </button>
        </div>
      </div>

      <div v-if="activeTab === 'models'" class="filter-card">
        <div class="filter-content">
          <el-input v-model="modelSearchKeyword" placeholder="搜索模型名称" class="filter-input" @keyup.enter="handleModelSearch">
            <template #prefix><el-icon><Search/></el-icon></template>
          </el-input>
          <button class="filter-btn" @click="handleModelSearch">
            <el-icon :size="13"><Search/></el-icon> 查询
          </button>
        </div>
      </div>
    </div>

    <div class="scroll-content">
      <!-- 训练任务表格 -->
      <div v-show="activeTab === 'training'" class="table-card">
        <div class="table-container">
          <el-table
            :data="tasks"
            v-loading="loading"
            element-loading-text="加载中..."
            style="width: 100%"
            :cell-style="{ textAlign: 'center' }"
            :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
            stripe
            empty-text="暂无训练任务"
            height="100%"
          >
            <el-table-column prop="id" label="任务ID" width="120">
              <template #default="{ row }">
                <span class="tid">#{{ row.id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="dataset_name" label="数据集名称" min-width="200">
              <template #default="{ row }">
                <span>{{ row.dataset_name || '未知数据集' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" effect="plain" round>
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="180">
              <template #default="{ row }">
                <el-progress :percentage="Math.floor(row.progress)" :stroke-width="10" :show-text="true" :color="getProgressColor(row.status)" />
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="180">
              <template #default="{ row }">
                <span class="t-time">{{ formatTime(row.start_time) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="结束时间" width="180">
              <template #default="{ row }">
                <span class="t-time">{{ formatTime(row.end_time) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="指标" width="330">
              <template #default="{ row }">
                <div v-if="row.metrics" class="t-metrics-row">
                  <div v-if="row.metrics.map50 !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">mAP50</span>
                    <span class="t-mr-val">{{ (row.metrics.map50 * 100).toFixed(1) }}%</span>
                  </div>
                  <div v-if="row.metrics['map50-95'] !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">mAP50-95</span>
                    <span class="t-mr-val">{{ (row.metrics['map50-95'] * 100).toFixed(1) }}%</span>
                  </div>
                  <div v-if="row.metrics.precision !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">Precision</span>
                    <span class="t-mr-val">{{ (row.metrics.precision * 100).toFixed(1) }}%</span>
                  </div>
                  <div v-if="row.metrics.recall !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">Recall</span>
                    <span class="t-mr-val">{{ (row.metrics.recall * 100).toFixed(1) }}%</span>
                  </div>
                </div>
                <span v-else class="t-na">-</span>
              </template>
            </el-table-column>
            <el-table-column label="创建人" width="120">
              <template #default="{ row }">
                <span class="t-user">{{ row.create_user_nickname || row.create_user || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <div class="t-actions">
                  <button class="t-act t-act-detail" @click="showTaskDetail(row)">详情</button>
                  <button v-if="row.status === 'pending' || row.status === 'running'" class="t-act t-act-abort" @click="abortTask(row)">放弃</button>
                  <button class="t-act t-act-del" @click="deleteTask(row.id)">删除</button>
                  <button v-if="row.status === 'failed'" class="t-act t-act-retry" @click="retryTask(row.id)">重试</button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 已训练模型表格 -->
      <div v-show="activeTab === 'models'" class="table-card">
        <div class="table-container">
          <el-table
            :data="models"
            v-loading="modelsLoading"
            element-loading-text="加载中..."
            style="width: 100%"
            :cell-style="{ textAlign: 'center' }"
            :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
            stripe
            empty-text="暂无训练好的模型"
            height="100%"
          >
            <el-table-column prop="id" label="模型ID" width="120">
              <template #default="{ row }">
                <span class="tid">#{{ row.id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="200">
              <template #default="{ row }">
                <el-tooltip :content="row.name" placement="top">
                  <span class="t-model-name">{{ row.name }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="dataset_id" label="数据集ID" width="110">
              <template #default="{ row }">
                <span class="tid">#{{ row.dataset_id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="dataset_name" label="数据集名称" min-width="180">
              <template #default="{ row }">
                <span>{{ row.dataset_name || '未知数据集' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="90">
              <template #default="{ row }">
                <span class="t-size">{{ formatFileSize(row.size) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="指标" min-width="280">
              <template #default="{ row }">
                <div v-if="row.metrics" class="t-metrics-row">
                  <div v-if="row.metrics.map50 !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">mAP50</span>
                    <span class="t-mr-val">{{ (row.metrics.map50 * 100).toFixed(1) }}%</span>
                  </div>
                  <div v-if="row.metrics['map50-95'] !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">mAP50-95</span>
                    <span class="t-mr-val">{{ (row.metrics['map50-95'] * 100).toFixed(1) }}%</span>
                  </div>
                  <div v-if="row.metrics.precision !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">Precision</span>
                    <span class="t-mr-val">{{ (row.metrics.precision * 100).toFixed(1) }}%</span>
                  </div>
                  <div v-if="row.metrics.recall !== undefined" class="t-mr-item">
                    <span class="t-mr-lbl">Recall</span>
                    <span class="t-mr-val">{{ (row.metrics.recall * 100).toFixed(1) }}%</span>
                  </div>
                </div>
                <span v-else class="t-na">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="生成时间" width="180">
              <template #default="{ row }">
                <span class="t-time">{{ formatTime(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <div class="t-actions">
                  <button class="t-act t-act-detail" @click="showModelDetail(row)">详情</button>
                  <button class="t-act t-act-test" @click="openTestModelDialog(row)">测试</button>
                  <button class="t-act t-act-del" @click="removeModel(row.id)">删除</button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 分页：训练任务 -->
    <div v-show="activeTab === 'training'" class="yt-page-footer">
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="(size) => { pagination.pageSize = size; loadTasks(1) }"
        @current-change="handlePageChange"
        background
        size="small"
      />
    </div>
    <!-- 分页：已训练模型 -->
    <div v-show="activeTab === 'models'" class="yt-page-footer">
      <el-pagination
        :current-page="modelPagination.page"
        :page-size="modelPagination.pageSize"
        :total="modelPagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="(size) => { modelPagination.pageSize = size; loadModels(1) }"
        @current-change="handleModelPageChange"
        background
        size="small"
      />
    </div>

    <!-- ===== 训练任务详情抽屉 ===== -->
    <el-drawer title="任务详情" v-model="drawerVisible" direction="rtl" size="500px" :with-header="true">
      <div v-if="currentTask" class="detail-content">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row"><span class="label">任务ID:</span><span class="value">#{{ currentTask.id }}</span></div>
          <div class="detail-row">
            <span class="label">状态:</span>
            <span class="value"><el-tag :type="getStatusType(currentTask.status)" effect="dark">{{ getStatusText(currentTask.status) }}</el-tag></span>
          </div>
        </div>
        <div class="detail-section">
          <h3>数据集信息</h3>
          <div class="detail-row"><span class="label">数据集ID:</span><span class="value">#{{ currentTask.dataset_id }}</span></div>
          <div class="detail-row"><span class="label">数据集名称:</span><span class="value">{{ currentTask.dataset_name || '未知数据集' }}</span></div>
          <div class="detail-row"><span class="label">图片数量:</span><span class="value">{{ currentTask.dataset_detail?.image_count || 0 }} 张</span></div>
          <div class="detail-row"><span class="label">标注实例:</span><span class="value">{{ currentTask.dataset_detail?.label_count || 0 }} 个</span></div>
          <div class="detail-row"><span class="label">类别数量:</span><span class="value">{{ currentTask.dataset_detail?.class_count || 0 }} 类</span></div>
        </div>
        <div class="detail-section">
          <h3>训练参数</h3>
          <div class="detail-row"><span class="label">基础模型:</span><span class="value">{{ currentTask.config?.model_name || currentTask.model_name }}</span></div>
          <div class="detail-row"><span class="label">训练轮数:</span><span class="value">{{ currentTask.config?.epochs || currentTask.total_epochs || 0 }} epochs</span></div>
          <div class="detail-row"><span class="label">批次大小:</span><span class="value">{{ currentTask.config?.batch_size || '-' }}</span></div>
          <div class="detail-row"><span class="label">图片尺寸:</span><span class="value">{{ currentTask.config?.imgsz || '-' }} px</span></div>
          <div class="detail-row"><span class="label">训练设备:</span><span class="value">{{ currentTask.config?.device || '-' }}</span></div>
          <div class="detail-row"><span class="label">学习率:</span><span class="value">{{ currentTask.config?.lr0 || '-' }}</span></div>
        </div>
        <div class="detail-section">
          <h3>时间信息</h3>
          <div class="detail-row"><span class="label">开始时间:</span><span class="value">{{ formatTime(currentTask.start_time) }}</span></div>
          <div class="detail-row"><span class="label">结束时间:</span><span class="value">{{ formatTime(currentTask.end_time) }}</span></div>
          <div class="detail-row"><span class="label">创建时间:</span><span class="value">{{ formatTime(currentTask.created_at) }}</span></div>
        </div>
      </div>
    </el-drawer>

    <!-- ===== 模型详情抽屉 ===== -->
    <el-drawer title="模型详情" v-model="modelDrawerVisible" direction="rtl" size="500px" :with-header="true">
      <div v-if="currentModel" class="detail-content">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row"><span class="label">模型ID:</span><span class="value">#{{ currentModel.id }}</span></div>
          <div class="detail-row"><span class="label">模型名称:</span><span class="value">{{ currentModel.name }}</span></div>
          <div class="detail-row"><span class="label">模型大小:</span><span class="value">{{ formatFileSize(currentModel.size) }}</span></div>
        </div>
        <div class="detail-section">
          <h3>数据集信息</h3>
          <div class="detail-row"><span class="label">数据集ID:</span><span class="value">#{{ currentModel.dataset_id }}</span></div>
          <div class="detail-row"><span class="label">数据集名称:</span><span class="value">{{ currentModel.dataset_name || '未知数据集' }}</span></div>
          <div class="detail-row"><span class="label">图片数量:</span><span class="value">{{ currentModel.dataset_detail?.image_count || 0 }} 张</span></div>
          <div class="detail-row"><span class="label">标注实例:</span><span class="value">{{ currentModel.dataset_detail?.label_count || 0 }} 个</span></div>
          <div class="detail-row"><span class="label">类别数量:</span><span class="value">{{ currentModel.dataset_detail?.class_count || 0 }} 类</span></div>
        </div>
        <div class="detail-section">
          <h3>训练参数</h3>
          <div class="detail-row"><span class="label">基础模型:</span><span class="value">{{ currentModel.config?.model_name || currentModel.model_name || '-' }}</span></div>
          <div class="detail-row"><span class="label">训练轮数:</span><span class="value">{{ currentModel.config?.epochs || '-' }} epochs</span></div>
          <div class="detail-row"><span class="label">批次大小:</span><span class="value">{{ currentModel.config?.batch_size || '-' }}</span></div>
          <div class="detail-row"><span class="label">图片尺寸:</span><span class="value">{{ currentModel.config?.imgsz || '-' }} px</span></div>
          <div class="detail-row"><span class="label">训练设备:</span><span class="value">{{ currentModel.config?.device || '-' }}</span></div>
        </div>
      </div>
    </el-drawer>

    <!-- ===== 删除训练任务确认 ===== -->
    <el-dialog v-model="showDeleteTaskDialog" width="420px" class="delete-dialog" :close-on-click-modal="false">
      <div class="text-center py-8">
        <div class="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <el-icon :size="32" class="text-red-500"><Warning/></el-icon>
        </div>
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除训练任务吗？</h3>
        <p class="text-gray-600 mb-2">任务ID：<em><strong>#{{ deleteTaskInfo.id }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">此操作不可撤销，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteTaskDialog = false" class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">取消</el-button>
          <el-button type="danger" @click="confirmDeleteTask" :disabled="deleteTaskCountdown > 0" class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-sm py-1.5 px-4 rounded-lg">{{ deleteTaskCountdown > 0 ? '确认删除 (' + deleteTaskCountdown + 's)' : '确定删除' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ===== 删除模型确认 ===== -->
    <el-dialog v-model="showDeleteModelDialog" width="420px" class="delete-dialog" :close-on-click-modal="false">
      <div class="text-center py-8">
        <div class="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <el-icon :size="32" class="text-red-500"><Warning/></el-icon>
        </div>
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除模型吗？</h3>
        <p class="text-gray-600 mb-2">模型名称：<em><strong>{{ deleteModelInfo.name }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">删除后模型文件将被永久删除且无法恢复，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteModelDialog = false" class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">取消</el-button>
          <el-button type="danger" @click="confirmDeleteModel" :disabled="deleteModelCountdown > 0" class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-sm py-1.5 px-4 rounded-lg">{{ deleteModelCountdown > 0 ? '确认删除 (' + deleteModelCountdown + 's)' : '确定删除' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ===== 测试模型弹窗 ===== -->
    <el-dialog v-model="showTestModelDialog" width="640px">
      <template #header>
        <div class="tm-dialog-header">
          <div class="tm-header-icon"><el-icon><Aim /></el-icon></div>
          <div class="tm-header-text">
            <span class="tm-title">测试模型</span>
            <span class="tm-subtitle">上传图片进行模型推理测试</span>
          </div>
        </div>
      </template>
      <div class="tm-section tm-section--blue">
        <div class="tm-section-header">
          <span class="tm-section-icon"><el-icon><UploadFilled /></el-icon></span>
          <span class="tm-section-title">选择图片</span>
        </div>
        <div class="tm-section-body">
          <el-upload ref="testUploadRef" :auto-upload="false" :file-list="testFiles" :on-change="handleTestFileChange" :on-remove="handleTestFileRemove" accept="image/*" drag>
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
          </el-upload>
        </div>
      </div>
      <div class="tm-section tm-section--amber">
        <div class="tm-section-header">
          <span class="tm-section-icon"><el-icon><TrendCharts /></el-icon></span>
          <span class="tm-section-title">置信度阈值</span>
          <span class="tm-section-value">{{ (confidenceThreshold * 100).toFixed(0) }}%</span>
        </div>
        <div class="tm-section-body">
          <el-slider v-model="confidenceThreshold" :min="0" :max="1" :step="0.05" />
        </div>
      </div>
      <div v-if="testResults" class="tm-section tm-section--green">
        <div class="tm-section-header">
          <span class="tm-section-icon"><el-icon><List /></el-icon></span>
          <span class="tm-section-title">检测结果</span>
          <span class="tm-section-badge">{{ testResults.predictions.length }} 个目标</span>
        </div>
        <div class="tm-section-body">
          <div class="tm-result-image">
            <img v-if="testImageUrl" :src="testImageUrl" alt="检测结果" class="tm-preview-img" @click="showImagePreview = true" />
            <p class="tm-image-hint">点击图片放大查看</p>
          </div>
          <div v-if="testResults.predictions.length > 0" class="tm-result-list">
            <div v-for="(result, index) in testResults.predictions" :key="index" class="tm-result-item">
              <span class="tm-result-name">{{ result.class_name }}</span>
              <span class="tm-result-conf" :class="confidenceLevel(result.confidence)">{{ (result.confidence * 100).toFixed(1) }}%</span>
            </div>
          </div>
          <div v-else class="tm-empty"><span>未检测到目标，请尝试降低置信度阈值</span></div>
        </div>
      </div>
      <div v-if="showImagePreview" class="image-preview-overlay" @click="closePreview">
        <div class="preview-container" @click.stop>
          <button class="close-btn" @click="closePreview">×</button>
          <div class="preview-controls">
            <button class="control-btn reset-btn" @click="resetView">↺</button>
            <span class="scale-info">{{ Math.round(scale * 100) }}%</span>
          </div>
          <div class="image-wrapper" @wheel="handleWheel" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp" @mouseleave="handleMouseUp" @dblclick="handleDoubleClick">
            <img ref="imageRef" :src="testImageUrl" alt="放大预览" class="preview-image" :style="{ transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`, cursor: scale > 1 ? 'grab' : 'default' }" />
          </div>
          <div class="preview-hint"><p>滚轮缩放 | 拖拽移动（放大后）</p></div>
        </div>
      </div>
      <template #footer>
        <el-button class="tm-btn-cancel" @click="showTestModelDialog = false">取消</el-button>
        <el-button class="tm-btn-primary" type="primary" @click="testModel" :loading="testing">开始测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, Warning, Search, List, Aim, UploadFilled, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteTrainTask, getTrainTasks, retryTrainTask, abortTrainTask } from '@/network/api.js'
import { getModelsList, deleteModel as deleteModelApi, predictImage } from '@/network/api'

// ===== Tab 切换 =====
const route = useRoute()
const router = useRouter()
const activeTab = ref(route.query.tab === 'models' ? 'models' : 'training')

const switchTab = (tab) => {
  activeTab.value = tab
  router.replace({ query: { tab } })
  if (tab === 'models' && models.value.length === 0) loadModels()
  if (tab === 'training' && tasks.value.length === 0) loadTasks()
}

const refreshCurrentTab = () => {
  if (activeTab.value === 'training') loadTasks()
  else loadModels()
}

// ===== 训练任务 =====
const tasks = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const currentTask = ref(null)
const showDeleteTaskDialog = ref(false)
const deleteTaskInfo = ref({ id: null })
const deleteTaskCountdown = ref(0)
let deleteTaskTimer = null
const deleteModelCountdown = ref(0)
let deleteModelTimer = null
const filterStatus = ref('')
const searchKeyword = ref('')

const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const loadTasks = async (page = pagination.value.page) => {
  loading.value = true
  try {
    const params = { page, page_size: pagination.value.pageSize }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchKeyword.value?.trim()) params.keyword = searchKeyword.value.trim()
    const resp = await getTrainTasks(params)
    if (resp.code === 0) {
      tasks.value = resp.data.tasks || []
      pagination.value.total = resp.data.total || 0
      pagination.value.page = resp.data.page || 1
    }
  } catch (error) { console.error('加载训练任务失败:', error) }
  finally { loading.value = false }
}

const handlePageChange = (page) => { pagination.value.page = page; loadTasks(page) }
const handleSearch = () => { pagination.value.page = 1; loadTasks(1) }

const abortTask = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要放弃任务"${row.dataset_name}"吗？`, '确认放弃', { confirmButtonText: '确定放弃', cancelButtonText: '取消', type: 'warning' })
    const resp = await abortTrainTask(row.id)
    if (resp.code === 0) { ElMessage.success('任务已放弃'); loadTasks() }
    else { ElMessage.error(resp.message || '操作失败') }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const deleteTask = (id) => {
  deleteTaskInfo.value = { id }
  showDeleteTaskDialog.value = true
  deleteTaskCountdown.value = 5
  clearInterval(deleteTaskTimer)
  deleteTaskTimer = setInterval(() => {
    deleteTaskCountdown.value--
    if (deleteTaskCountdown.value <= 0) {
      clearInterval(deleteTaskTimer)
      deleteTaskTimer = null
    }
  }, 1000)
}

const confirmDeleteTask = async () => {
  clearInterval(deleteTaskTimer)
  deleteTaskTimer = null
  try {
    const resp = await deleteTrainTask(deleteTaskInfo.value.id)
    if (resp.code === 0) { ElMessage.success('删除成功'); showDeleteTaskDialog.value = false; loadTasks() }
    else { ElMessage.error(resp.message || '删除失败') }
  } catch (error) { console.error('删除任务失败:', error); ElMessage.error('删除失败：网络或服务器错误') }
}

const retryTask = async (id) => {
  try {
    const resp = await retryTrainTask(id)
    if (resp.code === 0) { ElMessage.success('重试任务已提交'); loadTasks() }
    else { ElMessage.error(resp.message || '重试失败') }
  } catch (error) { console.error('重试任务失败:', error); ElMessage.error('重试失败：网络或服务器错误') }
}

const showTaskDetail = (task) => { currentTask.value = task; drawerVisible.value = true }

const getStatusType = (status) => ({ pending: 'info', running: 'warning', completed: 'success', failed: 'danger', aborted: 'warning' }[status] || 'info')
const getStatusText = (status) => ({ pending: '等待中', running: '训练中', completed: '已完成', failed: '失败', aborted: '已放弃' }[status] || status)
const getProgressColor = (status) => ({ pending: '#909399', running: '#409eff', completed: '#67c23a', failed: '#f56c6c', aborted: '#e6a23c' }[status] || '#409eff')

// ===== 已训练模型 =====
const models = ref([])
const modelsLoading = ref(false)
const modelDrawerVisible = ref(false)
const currentModel = ref(null)
const showDeleteModelDialog = ref(false)
const deleteModelInfo = ref({ id: null, name: '' })
const modelSearchKeyword = ref('')

const modelPagination = ref({ page: 1, pageSize: 20, total: 0 })

const loadModels = async (page = modelPagination.value.page) => {
  modelsLoading.value = true
  try {
    const params = { page, page_size: modelPagination.value.pageSize }
    if (modelSearchKeyword.value?.trim()) params.keyword = modelSearchKeyword.value.trim()
    const resp = await getModelsList(params)
    if (resp.code === 0) {
      models.value = resp.data.models || []
      modelPagination.value.total = resp.data.total || 0
      modelPagination.value.page = resp.data.page || 1
    }
  } catch (error) { console.error('加载模型列表失败:', error) }
  finally { modelsLoading.value = false }
}

const handleModelPageChange = (page) => { modelPagination.value.page = page; loadModels(page) }
const handleModelSearch = () => { modelPagination.value.page = 1; loadModels(1) }

const removeModel = (id) => {
  const model = models.value.find(m => m.id === id)
  deleteModelInfo.value = { id, name: model ? model.name : '未知模型' }
  showDeleteModelDialog.value = true
  deleteModelCountdown.value = 5
  clearInterval(deleteModelTimer)
  deleteModelTimer = setInterval(() => {
    deleteModelCountdown.value--
    if (deleteModelCountdown.value <= 0) {
      clearInterval(deleteModelTimer)
      deleteModelTimer = null
    }
  }, 1000)
}

const confirmDeleteModel = async () => {
  clearInterval(deleteModelTimer)
  deleteModelTimer = null
  try {
    const resp = await deleteModelApi(deleteModelInfo.value.id)
    if (resp.code === 0) { ElMessage.success('删除成功'); showDeleteModelDialog.value = false; loadModels() }
    else { ElMessage.error(resp.message || '删除失败') }
  } catch (error) { console.error('删除模型失败:', error); ElMessage.error('删除失败：网络或服务器错误') }
}

const showModelDetail = (model) => { currentModel.value = model; modelDrawerVisible.value = true }

// ===== 测试模型 =====
const showTestModelDialog = ref(false)
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
const testUploadRef = ref(null)

const openTestModelDialog = (model) => {
  currentTestModel.value = model
  testFiles.value = []
  testResults.value = null
  testImageUrl.value = ''
  confidenceThreshold.value = 0.25
  showTestModelDialog.value = true
}

const handleTestFileChange = (file, fileList) => {
  testFiles.value = fileList.slice(-1)
  testResults.value = null
  testImageUrl.value = ''
}

const handleTestFileRemove = (file, fileList) => {
  testFiles.value = fileList
  testResults.value = null
  testImageUrl.value = ''
}

const confidenceLevel = (conf) => conf >= 0.8 ? 'conf-high' : conf >= 0.5 ? 'conf-mid' : 'conf-low'

const testModel = async () => {
  if (testFiles.value.length === 0) { ElMessage.warning('请选择要测试的图片'); return }
  testing.value = true
  try {
    const file = testFiles.value[0].raw
    const resp = await predictImage(currentTestModel.value.id, file, { conf_threshold: confidenceThreshold.value, save_result: true })
    if (resp.code === 0) {
      testResults.value = resp.data
      testImageUrl.value = resp.data.result_image || ''
      if (testImageUrl.value && !testImageUrl.value.startsWith('http')) {
        testImageUrl.value = `${import.meta.env.VITE_APP_SERVER_URL}${testImageUrl.value}`
      }
      ElMessage.success('测试完成')
    } else { ElMessage.error(resp.message || '测试失败') }
  } catch (error) { console.error('测试模型失败:', error); ElMessage.error('测试失败：网络或服务器错误') }
  finally { testing.value = false }
}

const handleWheel = (e) => {
  e.preventDefault()
  const rect = e.currentTarget.getBoundingClientRect()
  const mouseX = e.clientX - rect.left - rect.width / 2
  const mouseY = e.clientY - rect.top - rect.height / 2
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(1, Math.min(10, scale.value + delta))
  const scaleRatio = newScale / scale.value
  position.value = { x: mouseX * (1 - scaleRatio) + position.value.x * scaleRatio, y: mouseY * (1 - scaleRatio) + position.value.y * scaleRatio }
  scale.value = newScale
}

const handleDoubleClick = (e) => {
  if (scale.value <= 1) {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - rect.width / 2
    const mouseY = e.clientY - rect.top - rect.height / 2
    const targetScale = 3.5
    const scaleRatio = targetScale / scale.value
    position.value = { x: mouseX * (1 - scaleRatio) + position.value.x * scaleRatio, y: mouseY * (1 - scaleRatio) + position.value.y * scaleRatio }
    scale.value = targetScale
  } else { resetView() }
}

const handleMouseDown = (e) => {
  if (scale.value <= 1) return; e.preventDefault()
  isDragging.value = true
  dragStart.value = { x: e.clientX - position.value.x, y: e.clientY - position.value.y }
}
const handleMouseMove = (e) => { if (!isDragging.value) return; e.preventDefault(); position.value = { x: e.clientX - dragStart.value.x, y: e.clientY - dragStart.value.y } }
const handleMouseUp = () => { isDragging.value = false }
const resetView = () => { scale.value = 1; position.value = { x: 0, y: 0 } }
const closePreview = () => { showImagePreview.value = false; scale.value = 1; position.value = { x: 0, y: 0 }; isDragging.value = false }

// ===== 通用工具 =====
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
}

const stopDeleteTaskCountdown = () => {
  clearInterval(deleteTaskTimer)
  deleteTaskTimer = null
  deleteTaskCountdown.value = 0
}
const stopDeleteModelCountdown = () => {
  clearInterval(deleteModelTimer)
  deleteModelTimer = null
  deleteModelCountdown.value = 0
}

watch(showDeleteTaskDialog, (val) => { if (!val) stopDeleteTaskCountdown() })
watch(showDeleteModelDialog, (val) => { if (!val) stopDeleteModelCountdown() })

onMounted(() => {
  if (activeTab.value === 'training') loadTasks()
  else loadModels()
})
</script>

<style scoped>
.yolo-training {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f5f5f5;
}

.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
  z-index: 100;
  padding-bottom: 10px;
  background: #f5f5f5;
}

.scroll-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 2px;
}

/* Header */
.yt-header-card { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; overflow: hidden; }
.yt-header-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; }
.yt-title-group { display: flex; align-items: center; gap: 12px; }
.yt-icon-wrap { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.yt-title { margin: 0; font-size: 17px; font-weight: 700; color: #1d1d1f; }
.yt-subtitle { margin: 2px 0 0; font-size: 12px; color: #8e8e93; }
.yt-header-actions { display: flex; gap: 8px; }

.yt-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 7px 14px;
  transition: all 0.15s ease;
}

.yt-btn-ghost {
  background: transparent;
  color: #505050;
  border: 1px solid #d1d5db;
}

.yt-btn-ghost:hover { background: #f0f0f0; }

/* Tabs */
.yt-header-tabs { border-top: 1px solid #f0f0f0; padding: 0 18px; }
.yt-tab-bar { display: flex; gap: 0; }
.yt-tab-item { display: flex; align-items: center; gap: 6px; padding: 10px 20px; font-size: 13px; font-weight: 500; color: #8e8e93; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s ease; }
.yt-tab-item:hover { color: #5b6ef7; }
.yt-tab-item.active { color: #5b6ef7; border-bottom-color: #5b6ef7; }

/* Filter */
.filter-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
}

.filter-content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 12px;
  color: #8e8e93;
  white-space: nowrap;
}

.filter-input {
  width: 200px;
}

.filter-select {
  width: 140px;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #f5f7fa;
  border: 1px solid #e4e8ec;
  color: #646a73;
  border-radius: 6px;
  font-size: 13px;
  padding: 7px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 500;
}

.filter-btn:hover {
  background: #e8eef3;
}

/* Table Card */
.table-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  overflow: hidden;
}

.table-container {
  padding: 0;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.yt-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }

/* Table cell elements */
.tid {
  font-family: monospace;
  font-size: 12px;
  color: #8e8e93;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 4px;
}

.t-time {
  font-size: 12px;
  color: #8e8e93;
}

.t-size {
  font-size: 12px;
  color: #8e8e93;
}

.t-model-name {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  cursor: pointer;
}

.t-model-name:hover {
  color: #5b6ef7;
}

.t-user {
  font-size: 12px;
  color: #8e8e93;
}

.t-na {
  color: #c0c4cc;
}

/* Metrics split columns */
.t-metrics-row {
  display: inline-flex;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  overflow: hidden;
  background: #fafafa;
}

.t-mr-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 10px;
  min-width: 52px;
}

.t-mr-item + .t-mr-item {
  border-left: 1px solid #e8e8e8;
}

.t-mr-lbl {
  display: block;
  font-size: 9px;
  color: #8e8e93;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 1px;
}

.t-mr-val {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #1d1d1f;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}

/* Actions */
.t-actions {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.t-act {
  border: none;
  border-radius: 6px;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.12s ease;
  font-weight: 500;
}

.t-act-detail { background: #eef2ff; color: #5b6ef7; }
.t-act-detail:hover { background: #dde3ff; }
.t-act-test { background: #ecfdf5; color: #059669; }
.t-act-test:hover { background: #d1fae5; }
.t-act-retry { background: #ecfdf5; color: #059669; }
.t-act-retry:hover { background: #d1fae5; }
.t-act-abort { background: #fffbeb; color: #d97706; }
.t-act-abort:hover { background: #fef3c7; }
.t-act-del { background: #fef2f2; color: #dc2626; }
.t-act-del:hover { background: #fee2e2; }

/* ===== 详情抽屉 ===== */
.detail-content { padding: 0 4px; }
.detail-section { margin-bottom: 24px; }
.detail-section h3 { font-size: 14px; font-weight: 600; color: #1f2937; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid #f3f4f6; }
.detail-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
.detail-row .label { color: #6b7280; }
.detail-row .value { color: #1f2937; font-weight: 500; text-align: right; }

/* ===== 测试模型弹窗 ===== */
.tm-dialog-header { display: flex; align-items: center; gap: 12px; padding: 4px 0; }
.tm-header-icon { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; background: #eef2ff; color: #5b6ef7; }
.tm-header-text { display: flex; flex-direction: column; gap: 2px; }
.tm-title { font-size: 16px; font-weight: 600; color: #1f2937; }
.tm-subtitle { font-size: 12px; color: #9ca3af; }

.tm-section { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 14px; overflow: hidden; }
.tm-section--blue { border-left: 3px solid #4b8af4; }
.tm-section--amber { border-left: 3px solid #e8962e; }
.tm-section--green { border-left: 3px solid #34d399; }
.tm-section-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 1px solid #f3f4f6; }
.tm-section--blue .tm-section-header { background: #f5f9fd; }
.tm-section--amber .tm-section-header { background: #fefaf5; }
.tm-section--green .tm-section-header { background: #f4fdf8; }
.tm-section-icon { width: 26px; height: 26px; min-width: 26px; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.tm-section--blue .tm-section-icon { background: #e8f0fe; color: #4b8af4; }
.tm-section--amber .tm-section-icon { background: #fef3e8; color: #e8962e; }
.tm-section--green .tm-section-icon { background: #e8faf0; color: #34d399; }
.tm-section-title { font-size: 13px; font-weight: 600; color: #374151; }
.tm-section-value { margin-left: auto; font-size: 12px; font-weight: 600; color: #e8962e; background: #fef3e8; padding: 1px 9px; border-radius: 10px; }
.tm-section-badge { margin-left: auto; font-size: 11px; font-weight: 600; color: #34d399; background: #e8faf0; padding: 1px 9px; border-radius: 10px; }
.tm-section-body { padding: 14px; }
.tm-result-image { text-align: center; margin-bottom: 14px; }
.tm-preview-img { max-width: 100%; max-height: 360px; border-radius: 8px; border: 1px solid #e5e7eb; cursor: pointer; transition: box-shadow 0.15s ease; }
.tm-preview-img:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
.tm-image-hint { font-size: 11px; color: #9ca3af; margin-top: 6px; }
.tm-result-list { display: flex; flex-wrap: wrap; gap: 8px; }
.tm-result-item { display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; }
.tm-result-name { font-weight: 500; color: #374151; }
.tm-result-conf { font-weight: 600; font-size: 12px; padding: 1px 7px; border-radius: 6px; }
.tm-result-conf.conf-high { background: #dcfce7; color: #16a34a; }
.tm-result-conf.conf-mid { background: #fef9c3; color: #ca8a04; }
.tm-result-conf.conf-low { background: #fee2e2; color: #dc2626; }
.tm-empty { text-align: center; padding: 20px; color: #9ca3af; font-size: 13px; }
.tm-btn-cancel, .tm-btn-primary { border-radius: 8px; font-size: 13px; }

.image-preview-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.85); display: flex; justify-content: center; align-items: center;
  z-index: 2000; cursor: pointer; backdrop-filter: blur(4px);
}
.preview-container {
  position: relative; width: 90vw; height: 90vh; display: flex; flex-direction: column; cursor: default;
}
.preview-controls {
  position: absolute; top: 10px; right: 60px; display: flex; gap: 10px; align-items: center; z-index: 10;
}
.control-btn {
  width: 36px; height: 36px; border: 2px solid rgba(255,255,255,0.8);
  background: rgba(0,0,0,0.7); color: white; font-size: 20px; cursor: pointer;
  border-radius: 50%; display: flex; justify-content: center; align-items: center;
  transition: all 0.2s ease; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}
.control-btn:hover { background: rgba(255,255,255,0.9); color: #333; }
.close-btn {
  position: absolute; top: 10px; right: 10px;
  width: 36px; height: 36px; border: 2px solid rgba(255,255,255,0.8);
  background: rgba(0,0,0,0.7); color: white; font-size: 20px; cursor: pointer;
  border-radius: 50%; display: flex; justify-content: center; align-items: center;
  transition: all 0.2s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.4); z-index: 100;
}
.close-btn:hover { background: rgba(255,255,255,0.9); color: #333; }
.scale-info {
  color: white; font-size: 14px; background: rgba(255,255,255,0.2);
  padding: 6px 12px; border-radius: 4px;
}
.image-wrapper {
  width: 100%; height: 100%; display: flex; justify-content: center;
  align-items: center; overflow: hidden;
}
.preview-image {
  max-width: 100%; max-height: 100%; object-fit: contain;
  transition: transform 0.1s ease-out;
}
.preview-hint {
  position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
  color: rgba(255,255,255,0.7); font-size: 14px;
}
</style>
