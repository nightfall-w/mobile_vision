<template>
  <div class="testplan-management">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">测试计划</h1>
          <p class="page-subtitle">管理工作空间下的测试计划</p>
        </div>
        <div class="header-right">
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

      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索测试计划名称"
          class="search-input"
          @keyup.enter="loadPlans"
        >
          <template #prefix>
            <el-icon><Search/></el-icon>
          </template>
        </el-input>
        <el-button class="search-btn" @click="loadPlans">
          <el-icon><Search/></el-icon>
          查询
        </el-button>
        <el-button class="reset-btn" @click="resetSearch">
          <el-icon><Refresh/></el-icon>
          重置
        </el-button>
        <el-button type="primary" @click="openCreateDialog" style="margin-left: auto">
          <el-icon :size="16" class="mr-1"><Plus/></el-icon>
          创建测试计划
        </el-button>
      </div>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
      <div class="table-container">
        <el-table
        :data="planList"
        v-loading="loading"
        element-loading-text="加载中..."
        style="width: 100%"
        border
        :cell-style="{ textAlign: 'center' }"
        :header-cell-style="{ textAlign: 'center', backgroundColor: '#f5f7fa', color: '#606266' }"
        empty-text="暂无测试计划"
        :height="tableHeight"
      >
        <el-table-column label="ID" width="64">
          <template #default="{ row }">
            <span class="id-text">#{{ row.plan_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="计划名称" min-width="130" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="100" show-overflow-tooltip />
        <el-table-column prop="case_count" label="用例数" width="70" />
        <el-table-column prop="create_time" label="创建时间" width="180" />
        <el-table-column label="操作" width="280" align="left">
            <template #default="{ row }">
              <div class="action-group">
                <span class="action-btn action-edit" @click="openEditDialog(row)">编辑</span>
                <span class="action-btn action-link" @click="openAddCaseDialog(row)">关联</span>
                <span class="action-btn action-run" @click="executePlan(row)">执行</span>
                <span class="action-btn action-view" @click="viewTasks(row)">任务</span>
                <span class="action-btn action-delete" @click="deletePlan(row)">删除</span>
              </div>
            </template>
          </el-table-column>
      </el-table>
    </div>

    <div class="table-footer">
        <el-pagination
          :current-page="pageNum"
          :page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
          background
        />
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      width="500px"
      class="cp-dialog"
      destroy-on-close
      align-center
      @close="resetForm"
    >
      <template #header>
        <div class="cp-header">
          <div class="cp-header-title">{{ dialogTitle }}</div>
          <div class="cp-header-subtitle">{{ dialogTitle === '创建测试计划' ? '创建一个新计划来组织你的测试用例' : '修改测试计划的基本信息' }}</div>
        </div>
      </template>

      <el-form :model="form" label-position="top" class="cp-form">
        <el-form-item label="计划名称" prop="name">
          <el-input v-model="form.name" placeholder="例：V3.2 回归测试" maxlength="100" />
        </el-form-item>
        <el-form-item label="计划描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述该计划的目的和范围（选填）" maxlength="500" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="cp-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="savePlan">{{ dialogTitle === '创建测试计划' ? '创建计划' : '保存修改' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="viewDialogVisible"
      title="计划详情"
      width="600px"
    >
      <div v-if="currentPlan" class="view-content">
        <div class="view-section">
          <h3 class="section-title">基本信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">计划名称</span>
              <span class="info-value">{{ currentPlan.name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">关联用例数</span>
              <span class="info-value">{{ currentPlan.case_count || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="view-section">
          <h3 class="section-title">计划描述</h3>
          <div class="content-box">
            <pre class="content-text">{{ currentPlan.description || '无' }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="executeDialogVisible"
      :title="`执行计划 - ${selectedPlan?.name || ''}`"
      width="560px"
    >
      <div class="execute-info">
        <p>计划包含 <strong>{{ currentPlan?.case_count || 0 }}</strong> 个测试用例</p>
        <div class="device-summary">
          <div class="summary-item">
            <span class="summary-label">指定设备:</span>
            <span class="summary-value">{{ specifiedDeviceCount }} 个</span>
          </div>
          <div class="summary-item dynamic">
            <span class="summary-label">动态分配:</span>
            <span class="summary-value">{{ dynamicAssignCount }} 个</span>
          </div>
        </div>
        <p class="tip">
          <el-icon class="tip-icon"><InfoFilled/></el-icon>
          动态分配的用例会自动分配给当前空闲的在线设备
        </p>
      </div>
      <template #footer>
        <el-button @click="executeDialogVisible = false">取消</el-button>
        <el-button type="success" @click="confirmExecute">确认执行</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="deleteDialogVisible"
      title="确认删除"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="text-center py-4">
        <el-icon :size="48" class="text-red-500 mb-4"><Warning/></el-icon>
        <p class="text-gray-700">确定要删除测试计划 <strong>{{ deletePlanData?.name }}</strong> 吗？</p>
        <p class="text-gray-500 text-sm mt-2">此操作不可撤销，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="deleteDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="confirmDelete">确定删除</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="addCaseDialogVisible"
      :title="`关联用例 - ${selectedPlan?.name || ''}`"
      width="1200px"
      class="case-management-dialog"
      @open="handleDialogOpen"
      @close="handleDialogClose"
      destroy-on-close
    >
      <el-tabs v-model="activeTab" class="case-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="添加用例" name="add">
          <div class="add-case-tab">
            <div class="tab-toolbar">
              <div class="toolbar-left">
                <el-input
                  v-model="searchKeyword"
                  placeholder="搜索用例名称"
                  clearable
                  size="default"
                  style="width: 240px;"
                  @input="handleSearchCases"
                >
                  <template #prefix>
                    <el-icon><Search/></el-icon>
                  </template>
                </el-input>
              </div>
            </div>
            <el-table
              ref="addTableRef"
              :data="availableCaseList"
              v-loading="caseLoading"
              @selection-change="handleSelectionChange"
              border
              class="case-table"
              style="width: 100%"
              height="380"
            >
              <el-table-column type="selection" width="50" />
              <el-table-column prop="case_name" label="用例名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="level" label="优先级" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.level === 'P0' ? 'danger' : row.level === 'P1' ? 'warning' : 'info'">
                    {{ row.level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="updater_name" label="更新人" width="100" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'disabled' ? 'info' : 'warning'">
                    {{ row.status === 'completed' ? '已完成' : row.status === 'disabled' ? '已禁用' : '调试中' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="selectedToAdd.length > 0" class="batch-config-bar">
              <span class="batch-label">已选 <strong>{{ selectedToAdd.length }}</strong> 个用例</span>
              <el-select v-model="batchDeviceId" placeholder="选择执行设备" size="default" style="width: 220px">
                <el-option label="🔄 动态分配（空闲设备）" :value="''" />
                <el-option
                  v-for="d in deviceOptions"
                  :key="d.id"
                  :label="`${d.brand} ${d.model} (${d.id})`"
                  :value="d.id"
                />
              </el-select>
              <el-select v-model="batchLLMId" placeholder="选择LLM" size="default" style="width: 200px">
                <el-option
                  v-for="l in llmOptions"
                  :key="l.id"
                  :label="`${l.model} (${l.base_url || 'N/A'})`"
                  :value="l.id"
                />
              </el-select>
              <el-select v-model="batchYOLOId" placeholder="选择YOLO" size="default" style="width: 140px">
                <el-option
                  v-for="y in yoloOptions"
                  :key="y.id"
                  :label="y.name"
                  :value="y.id"
                />
              </el-select>
              <el-button type="primary" @click="batchAddCases" size="default">
                添加 ({{ selectedToAdd.length }})
              </el-button>
            </div>
            <div class="table-pagination">
              <el-pagination
                v-model:current-page="casePagination.page_num"
                v-model:page-size="casePagination.page_size"
                :page-sizes="[10, 20, 50]"
                :total="casePagination.total"
                layout="total, prev, pager, next"
                @size-change="handleCaseSizeChange"
                @current-change="handleCaseCurrentChange"
                size="small"
              />
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="已关联用例" name="associated">
          <div class="associated-case-tab">
            <div class="associated-stats">
              <span class="stat-total">已关联 <strong>{{ associatedCaseList.length }}</strong> 个用例</span>
              <span class="stat-divider">|</span>
              <span class="stat-specified">指定设备 <strong>{{ specifiedDeviceCount }}</strong></span>
              <span class="stat-divider">|</span>
              <span class="stat-dynamic">动态分配 <strong>{{ dynamicAssignCount }}</strong></span>
            </div>
            <div class="tab-toolbar">
              <el-button type="danger" size="small" @click="batchRemoveRelations" :disabled="selectedToRemove.length === 0">
                批量删除 ({{ selectedToRemove.length }})
              </el-button>
            </div>
            <el-table
              ref="associatedTableRef"
              :data="associatedCaseList"
              @selection-change="handleAssociatedSelectionChange"
              border
              class="case-table"
              style="width: 100%"
              height="410"
            >
              <el-table-column type="selection" width="50" />
              <el-table-column prop="case_name" label="用例名称" min-width="150" show-overflow-tooltip />
              <el-table-column prop="case_level" label="优先级" width="70">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.case_level === 'P0' ? 'danger' : row.case_level === 'P1' ? 'warning' : 'info'">
                    {{ row.case_level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'disabled' ? 'info' : 'warning'">
                    {{ row.status === 'completed' ? '已完成' : row.status === 'disabled' ? '已禁用' : '调试中' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="设备" min-width="160">
                <template #default="{ row }">
                  <el-tag v-if="row.device_id" size="small" class="device-tag">
                    <el-icon :size="12"><Iphone/></el-icon>
                    {{ row.device_name || row.device_id }}
                  </el-tag>
                  <el-tag v-else size="small" type="warning" class="dynamic-tag">
                    🔄 动态分配
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="LLM" min-width="120">
                <template #default="{ row }">
                  <span class="config-text">{{ getLLMName(row.llm_credential_id) || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="YOLO" width="100">
                <template #default="{ row }">
                  <span class="config-text">{{ getYOLOName(row.yolo_model_id) || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="OCR" width="80">
                <template #default="{ row }">
                  <span class="config-text">{{ row.ocr_engine || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="推理" width="80">
                <template #default="{ row }">
                  <span class="config-text">{{ row.reasoning_effort || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" size="small" link @click="openEditRelationDialog(row)">
                    <el-icon :size="15"><Edit/></el-icon>
                  </el-button>
                  <el-button type="danger" size="small" link @click="removeRelation(row.id)">
                    <el-icon :size="15"><Delete/></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 编辑关联用例配置弹窗 -->
    <el-dialog
      v-model="editRelationDialogVisible"
      width="640px"
      class="er-dialog"
      destroy-on-close
      align-center
    >
      <template #header>
        <div class="er-header">
          <div class="er-header-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="er-header-text">
            <div class="er-header-title">编辑用例配置</div>
            <div class="er-header-subtitle">为该用例单独覆盖计划默认配置</div>
          </div>
        </div>
      </template>

      <div class="er-case-card">
        <div class="er-case-card-name">{{ editRelationForm.case_name || '未命名用例' }}</div>
        <div class="er-case-card-meta">
          <el-tag
            v-if="editRelationForm.case_level"
            size="small"
            :type="editRelationForm.case_level === 'P0' ? 'danger' : editRelationForm.case_level === 'P1' ? 'warning' : 'info'"
            effect="light"
            round
          >
            {{ editRelationForm.case_level }}
          </el-tag>
          <el-tag
            v-if="editRelationForm.status"
            size="small"
            :type="editRelationForm.status === 'completed' ? 'success' : editRelationForm.status === 'disabled' ? 'info' : 'warning'"
            effect="plain"
            round
          >
            {{ editRelationForm.status === 'completed' ? '已完成' : editRelationForm.status === 'disabled' ? '已禁用' : '调试中' }}
          </el-tag>
        </div>
      </div>

      <el-form :model="editRelationForm" label-position="top" class="er-form">
        <!-- 执行环境 -->
        <div class="er-group">
          <div class="er-group-title-row">
            <span class="er-group-icon"><el-icon><Monitor /></el-icon></span>
            <span class="er-group-title">执行环境</span>
          </div>
          <div class="er-group-body">
            <el-form-item>
              <template #label>
                <span class="er-field-label">
                  执行设备
                  <span v-if="!editRelationForm.device_id" class="er-field-tag er-field-tag--dynamic">动态分配</span>
                  <span v-else class="er-field-tag er-field-tag--specified">已指定</span>
                </span>
              </template>
              <el-select v-model="editRelationForm.device_id" placeholder="选择执行设备" clearable style="width: 100%">
                <el-option label="动态分配（空闲设备）" :value="''" />
                <el-option
                  v-if="editRelationForm.device_id && !deviceOptions.some(d => d.id === editRelationForm.device_id)"
                  :key="`offline-${editRelationForm.device_id}`"
                  :label="`${editRelationForm.device_name || editRelationForm.device_id} (${editRelationForm.device_id})`"
                  :value="editRelationForm.device_id"
                />
                <el-option
                  v-for="d in deviceOptions"
                  :key="d.id"
                  :label="`${d.brand} ${d.model} (${d.id})`"
                  :value="d.id"
                />
              </el-select>
              <div class="er-field-hint">留空时由系统自动选择当前空闲的设备执行</div>
            </el-form-item>
          </div>
        </div>

        <!-- AI 模型 -->
        <div class="er-group">
          <div class="er-group-title-row">
            <span class="er-group-icon"><el-icon><MagicStick /></el-icon></span>
            <span class="er-group-title">AI 模型</span>
          </div>
          <div class="er-group-body er-group-body--grid">
            <el-form-item>
              <template #label>
                <span class="er-field-label">LLM 视觉模型</span>
              </template>
              <el-select v-model="editRelationForm.llm_credential_id" placeholder="选择 LLM" clearable style="width: 100%">
                <el-option
                  v-for="l in llmOptions"
                  :key="l.id"
                  :label="`${l.model} (${l.base_url || 'N/A'})`"
                  :value="l.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <template #label>
                <span class="er-field-label">YOLO 检测模型</span>
              </template>
              <el-select v-model="editRelationForm.yolo_model_id" placeholder="选择 YOLO" clearable style="width: 100%">
                <el-option
                  v-for="y in yoloOptions"
                  :key="y.id"
                  :label="y.name"
                  :value="y.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item class="er-form-item--full">
              <template #label>
                <span class="er-field-label">OCR 引擎</span>
              </template>
              <el-select v-model="editRelationForm.ocr_engine" placeholder="选择 OCR" clearable style="width: 100%">
                <el-option label="EasyOCR" value="easyocr" />
                <el-option label="RapidOCR" value="rapidocr" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <!-- 推理参数 -->
        <div class="er-group">
          <div class="er-group-title-row">
            <span class="er-group-icon"><el-icon><TrendCharts /></el-icon></span>
            <span class="er-group-title">推理参数</span>
          </div>
          <div class="er-group-body">
            <el-form-item>
              <template #label>
                <span class="er-field-label">推理强度</span>
              </template>
              <div class="er-reasoning-slider">
                <div class="er-slider-bar">
                  <div class="er-slider-track">
                    <div class="er-slider-fill" :style="{ width: reasoningEffortFill + '%' }"></div>
                  </div>
                  <div
                    v-for="(opt, i) in reasoningOptions"
                    :key="opt.value"
                    class="er-slider-stop"
                    :class="{ active: editRelationForm.reasoning_effort === opt.value }"
                    :style="{ left: (5 + i * 90 / (reasoningOptions.length - 1)) + '%' }"
                    @click="editRelationForm.reasoning_effort = opt.value"
                  >
                    <div class="er-slider-dot"></div>
                  </div>
                </div>
                <div class="er-slider-labels">
                  <div
                    v-for="(opt, i) in reasoningOptions"
                    :key="opt.value"
                    class="er-slider-label"
                    :class="{ active: editRelationForm.reasoning_effort === opt.value }"
                    :style="{ left: (5 + i * 90 / (reasoningOptions.length - 1)) + '%' }"
                    @click="editRelationForm.reasoning_effort = opt.value"
                  >
                    <span class="er-slider-label-text">{{ opt.label }}</span>
                    <span class="er-slider-label-sub">{{ opt.sub }}</span>
                  </div>
                </div>
              </div>
              <div class="er-field-hint">均衡模式适合大多数场景，深度模式适合复杂推理任务（耗时更长）</div>
            </el-form-item>
          </div>
        </div>
      </el-form>

      <template #footer>
        <div class="er-footer">
          <el-button @click="editRelationDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmEditRelation">保存配置</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh, Warning, User, InfoFilled, Iphone, Edit, Delete, Setting, Document, DocumentAdd, MagicStick, Cpu, Check, Monitor, Aim, TrendCharts } from '@element-plus/icons-vue'
import axios from '@/network/axios'
import {
  getTestPlanList,
  getTestPlanDetail,
  createTestPlan,
  updateTestPlan,
  deleteTestPlan,
  executeTestPlan,
  addCaseToPlan,
  updateCaseRelation,
  removeCaseRelation,
  getDeviceList,
  getLLMCredentialList,
  getModelsList,
  getTestCaseList,
  getWorkspaceDetail
} from '@/network/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
import { useRoute } from 'vue-router'

const route = useRoute()
const workspaceId = ref(1)

const planList = ref([])
const loading = ref(false)
const pageNum = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchKeyword = ref('')

const dialogVisible = ref(false)
const dialogTitle = ref('')
const viewDialogVisible = ref(false)
const addCaseDialogVisible = ref(false)
const editRelationDialogVisible = ref(false)
const executeDialogVisible = ref(false)
const deleteDialogVisible = ref(false)

const currentPlan = ref(null)
const selectedPlan = ref(null)
const deletePlanData = ref(null)

const deviceOptions = ref([])
const llmOptions = ref([])
const yoloOptions = ref([])

const availableCaseList = ref([])
const associatedCaseList = ref([])
const caseLoading = ref(false)
const selectedToAdd = ref([])
const selectedToRemove = ref([])
const batchDeviceId = ref('')  // 默认为空表示动态分配
const batchLLMId = ref(null)
const batchYOLOId = ref(null)
const addTableRef = ref(null)
const associatedTableRef = ref(null)
const casePagination = reactive({
  page_num: 1,
  page_size: 20,
  total: 0
})
const activeTab = ref('add')
const editRelationForm = reactive({
  id: null,
  device_id: '',
  device_name: '',
  llm_credential_id: null,
  yolo_model_id: null,
  ocr_engine: null,
  reasoning_effort: null,
  case_name: '',
  case_level: '',
  status: ''
})

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

const reasoningOptions = [
  { value: 'none', label: '关闭', sub: '无推理' },
  { value: 'low', label: '快速', sub: '低强度' },
  { value: 'medium', label: '均衡', sub: '中强度' },
  { value: 'high', label: '深度', sub: '高强度' }
]

const reasoningEffortFill = computed(() => {
  const map = { none: 5, low: 35, medium: 65, high: 100 }
  return map[editRelationForm.reasoning_effort] ?? 5
})

// 统计设备分配情况
const specifiedDeviceCount = computed(() => {
  return associatedCaseList.value.filter(r => r.device_id && r.device_id !== '').length
})

const dynamicAssignCount = computed(() => {
  return associatedCaseList.value.filter(r => !r.device_id || r.device_id === '').length
})

const workspaceName = ref('')
const managers = ref([])
const managerNames = computed(() => managers.value.map(m => m.nickname).join('、'))

const fetchWorkspaceDetail = async () => {
  try {
    const res = await getWorkspaceDetail({ workspace_id: workspaceId.value })
    if (res.code === 0) {
      workspaceName.value = res.data.workspace_name
      managers.value = res.data.manager || []
    }
  } catch (error) {
    console.error('获取工作空间详情失败:', error)
  }
}

const form = reactive({
  plan_id: null,
  name: '',
  description: ''
})

const formatTime = (time) => {
  if (!time) return '-'
  return time.replace('T', ' ')
}

const loadPlans = async () => {
  loading.value = true
  try {
    const result = await getTestPlanList({
      workspace_id: workspaceId.value,
      page_num: pageNum.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value
    })
    if (result.code === 0) {
      planList.value = result.data.list || []
      total.value = result.data.total || 0
    }
  } catch (error) {
    console.error('获取计划列表失败:', error)
    ElMessage.error('获取计划列表失败')
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchKeyword.value = ''
  pageNum.value = 1
  loadPlans()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  pageNum.value = 1
  loadPlans()
}

const handlePageChange = (page) => {
  pageNum.value = page
  loadPlans()
}

const openCreateDialog = () => {
  dialogTitle.value = '创建测试计划'
  form.plan_id = null
  form.name = ''
  form.description = ''
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  dialogTitle.value = '编辑测试计划'
  form.plan_id = row.plan_id
  form.name = row.name
  form.description = row.description || ''
  dialogVisible.value = true
}

const savePlan = async () => {
  if (!form.name) {
    ElMessage.error('请输入计划名称')
    return
  }

  const params = {
    name: form.name,
    description: form.description,
    workspace_id: workspaceId.value
  }
  if (form.plan_id) {
    params.plan_id = form.plan_id
  }

  const result = form.plan_id ? await updateTestPlan(params) : await createTestPlan(params)
  if (result.code === 0) {
    ElMessage.success(form.plan_id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadPlans()
  } else {
    ElMessage.error(result.message)
  }
}

const resetForm = () => {
  form.plan_id = null
  form.name = ''
  form.description = ''
}

const handleDialogOpen = async () => {
  activeTab.value = 'add'
  selectedToAdd.value = []
  selectedToRemove.value = []
  casePagination.page_num = 1
  casePagination.page_size = 20
  // 默认为动态分配
  batchDeviceId.value = ''
  batchLLMId.value = null
  batchYOLOId.value = null

  const planId = selectedPlan.value?.plan_id
  if (!planId) return

  try {
    const detailResult = await getTestPlanDetail(planId)
    if (detailResult.code === 0) {
      const relations = detailResult.data.relations || []
      associatedCaseList.value = relations
    } else {
      associatedCaseList.value = []
    }

    const [llmResult, yoloResult] = await Promise.all([
      getLLMCredentialList({}),
      getModelsList({ page: 1, page_size: 50, workspace_id: 1, model_type: 'yolo' })
    ])
    llmOptions.value = llmResult.code === 0 ? llmResult.data.list.map(l => ({ id: l.id, model: l.model, base_url: l.base_url })) : []
    yoloOptions.value = yoloResult.code === 0 ? yoloResult.data.models : []

    const [caseResult, devicesResult] = await Promise.all([
      getTestCaseList({ workspace_id: 1, page_num: casePagination.page_num, page_size: casePagination.page_size }),
      getDeviceList()
    ])

    if (caseResult.code === 0) {
      const allCases = caseResult.data.cases || []
      const associatedIds = associatedCaseList.value.map(r => r.case_id)
      availableCaseList.value = allCases.filter(c => !associatedIds.includes(c.case_id))
      casePagination.total = caseResult.data.total || 0
    } else {
      availableCaseList.value = []
      casePagination.total = 0
    }

    deviceOptions.value = devicesResult.code === 0 ? devicesResult.data : []

    // 设置默认值
    if (llmOptions.value.length > 0 && !batchLLMId.value) {
      batchLLMId.value = llmOptions.value[0].id
    }
    if (yoloOptions.value.length > 0 && !batchYOLOId.value) {
      batchYOLOId.value = yoloOptions.value[0].id
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

const handleTabChange = async (tab) => {
  if (tab === 'add') {
    await fetchAvailableCases()
  }
}

const fetchAvailableCases = async () => {
  caseLoading.value = true
  try {
    const result = await getTestCaseList({
      workspace_id: 1,
      page_num: casePagination.page_num,
      page_size: casePagination.page_size,
      case_name: searchKeyword.value
    })
    if (result.code === 0) {
      const allCases = result.data.cases || []
      const associatedIds = associatedCaseList.value.map(r => r.case_id)
      availableCaseList.value = allCases.filter(c => !associatedIds.includes(c.case_id))
      casePagination.total = result.data.total || 0
    } else {
      availableCaseList.value = []
      casePagination.total = 0
    }
  } catch (error) {
    console.error('获取用例列表失败:', error)
    availableCaseList.value = []
  } finally {
    caseLoading.value = false
  }
}

const handleDialogClose = () => {
  selectedToAdd.value = []
  selectedToRemove.value = []
  availableCaseList.value = []
  associatedCaseList.value = []
}

const handleSelectionChange = (selection) => {
  selectedToAdd.value = selection
}

const handleAssociatedSelectionChange = (selection) => {
  selectedToRemove.value = selection
}

const handleSearchCases = () => {
  casePagination.page_num = 1
  fetchAvailableCases()
}

const handleCaseSizeChange = (val) => {
  casePagination.page_size = val
  casePagination.page_num = 1
  fetchAvailableCases()
}

const handleCaseCurrentChange = (val) => {
  casePagination.page_num = val
  fetchAvailableCases()
}

const fetchCaseList = async () => {
  caseLoading.value = true
  try {
    const result = await axios.get('/api/v1/testcase/list', {
      workspace_id: workspaceId.value,
      page_num: casePagination.page_num,
      page_size: casePagination.page_size,
      case_name: searchKeyword.value
    })
    if (result.code === 0) {
      const allCases = result.data.cases || []
      const associatedIds = associatedCaseList.value.map(r => r.case_id)
      availableCaseList.value = allCases.filter(c => !associatedIds.includes(c.case_id))
      casePagination.total = result.data.total || 0
    } else {
      availableCaseList.value = []
      casePagination.total = 0
    }
  } catch (error) {
    console.error('获取用例列表失败:', error)
    availableCaseList.value = []
  } finally {
    caseLoading.value = false
  }
}

const batchAddCases = async () => {
  if (selectedToAdd.value.length === 0) {
    ElMessage.warning('请选择要添加的用例')
    return
  }

  const planId = selectedPlan.value?.plan_id
  if (!planId) return

  // 使用用户选择的设备或动态分配
  let deviceId = batchDeviceId.value
  let deviceName = ''
  let deviceAndroidId = ''

  if (deviceId === '') {
    // 动态分配: 不指定设备
    deviceId = null
    deviceName = null
    deviceAndroidId = null
  } else {
    // 指定了具体设备
    const device = deviceOptions.value.find(d => d.id === deviceId)
    if (device) {
      deviceName = `${device.brand} ${device.model}`
      deviceAndroidId = device.android_id
    } else if (deviceOptions.value.length > 0) {
      // fallback to first device if selection invalid
      deviceId = deviceOptions.value[0].id
      deviceName = `${deviceOptions.value[0].brand} ${deviceOptions.value[0].model}`
      deviceAndroidId = deviceOptions.value[0].android_id
    }
  }

  const llmId = batchLLMId.value || (llmOptions.value[0]?.id)
  const yoloId = batchYOLOId.value || (yoloOptions.value[0]?.id)

  if (!llmId || !yoloId) {
    ElMessage.error('LLM和YOLO模型未加载完成')
    return
  }

  try {
    let successCount = 0
    for (const item of selectedToAdd.value) {
      const result = await addCaseToPlan({
        plan_id: planId,
        case_id: item.case_id,
        device_id: deviceId,
        device_name: deviceName,
        device_android_id: deviceAndroidId,
        llm_credential_id: llmId,
        yolo_model_id: yoloId,
        ocr_engine: 'rapidocr',
        reasoning_effort: 'low'
      })
      if (result.code === 0) {
        successCount++
      }
    }

    if (successCount > 0) {
      const addedIds = selectedToAdd.value.map(c => c.case_id)
      availableCaseList.value = availableCaseList.value.filter(c => !addedIds.includes(c.case_id))
      selectedToAdd.value = []
      if (addTableRef.value) {
        addTableRef.value.clearSelection()
      }
      const deviceText = deviceId ? '指定设备' : '动态分配'
      ElMessage.success(`成功添加 ${successCount} 个用例 (${deviceText})`)
      activeTab.value = 'associated'
      await refreshAssociatedCases()
    }
  } catch (error) {
    console.error('添加用例失败:', error)
    ElMessage.error('添加用例失败')
  }
}

const refreshAssociatedCases = async () => {
  const planId = selectedPlan.value?.plan_id
  if (!planId) return

  try {
    const result = await getTestPlanDetail(planId)
    if (result.code === 0) {
      const relations = result.data.relations || []
      associatedCaseList.value = relations
    }
  } catch (error) {
    console.error('刷新已关联用例失败:', error)
  }
}

const getLLMName = (id) => {
  if (!id) return null
  const llm = llmOptions.value.find(l => l.id === id)
  return llm ? llm.model : id
}

const getYOLOName = (id) => {
  if (!id) return null
  const yolo = yoloOptions.value.find(y => y.id === id)
  return yolo ? yolo.name : id
}

const openEditRelationDialog = (row) => {
  editRelationForm.id = row.id
  editRelationForm.device_id = row.device_id || ''
  editRelationForm.device_name = row.device_name || ''
  editRelationForm.llm_credential_id = row.llm_credential_id || null
  editRelationForm.yolo_model_id = row.yolo_model_id || null
  editRelationForm.ocr_engine = row.ocr_engine || null
  editRelationForm.reasoning_effort = row.reasoning_effort || null
  editRelationForm.case_name = row.case_name || ''
  editRelationForm.case_level = row.case_level || ''
  editRelationForm.status = row.status || ''
  editRelationDialogVisible.value = true
}

const confirmEditRelation = async () => {
  try {
    const params = { id: editRelationForm.id }
    if (editRelationForm.device_id !== undefined) params.device_id = editRelationForm.device_id
    if (editRelationForm.llm_credential_id !== undefined) params.llm_credential_id = editRelationForm.llm_credential_id
    if (editRelationForm.yolo_model_id !== undefined) params.yolo_model_id = editRelationForm.yolo_model_id
    if (editRelationForm.ocr_engine !== undefined) params.ocr_engine = editRelationForm.ocr_engine
    if (editRelationForm.reasoning_effort !== undefined) params.reasoning_effort = editRelationForm.reasoning_effort

    const result = await updateCaseRelation(params)
    if (result.code === 0) {
      ElMessage.success('更新成功')
      editRelationDialogVisible.value = false
      await refreshAssociatedCases()
    } else {
      ElMessage.error(result.message || '更新失败')
    }
  } catch (error) {
    console.error('更新关联失败:', error)
    ElMessage.error('更新失败')
  }
}

const removeRelation = async (relationId) => {
  try {
    const result = await removeCaseRelation({ id: relationId })
    if (result.code === 0) {
      associatedCaseList.value = associatedCaseList.value.filter(r => r.id !== relationId)
      await fetchAvailableCases()
      ElMessage.success('删除成功')
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

const batchRemoveRelations = async () => {
  if (selectedToRemove.value.length === 0) {
    ElMessage.warning('请选择要删除的用例')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedToRemove.value.length} 个用例关联吗？`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )

    for (const item of selectedToRemove.value) {
      await removeCaseRelation({ id: item.id })
    }

    await refreshAssociatedCases()
    await fetchAvailableCases()
    selectedToRemove.value = []
    if (associatedTableRef.value) {
      associatedTableRef.value.clearSelection()
    }
    ElMessage.success('批量删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

const openAddCaseDialog = async (row) => {
  selectedPlan.value = row
  currentPlan.value = row
  addCaseDialogVisible.value = true
}

const executePlan = async (row) => {
  selectedPlan.value = row
  currentPlan.value = row
  try {
    const result = await getTestPlanDetail(row.plan_id)
    if (result.code === 0) {
      associatedCaseList.value = result.data.relations || []
    } else {
      associatedCaseList.value = []
    }
  } catch (error) {
    console.error('加载计划详情失败:', error)
    associatedCaseList.value = []
  }
  executeDialogVisible.value = true
}

const viewTasks = (row) => {
  router.push({
    name: 'TestTaskList',
    params: { id: row.workspace_id },
    query: {
      plan_id: row.plan_id
    }
  })
}

const confirmExecute = async () => {
  const result = await executeTestPlan({
    plan_id: selectedPlan.value.plan_id
  })
  if (result.code === 0) {
    ElMessage.success(result.message)
    executeDialogVisible.value = false
  } else {
    ElMessage.error(result.message)
  }
}

const deletePlan = (row) => {
  deletePlanData.value = row
  deleteDialogVisible.value = true
}

const confirmDelete = async () => {
  const result = await deleteTestPlan({
    plan_id: deletePlanData.value.plan_id
  })
  if (result.code === 0) {
    ElMessage.success('删除成功')
    deleteDialogVisible.value = false
    loadPlans()
  } else {
    ElMessage.error(result.message)
  }
}

onMounted(() => {
  const id = route.params.id
  if (id) {
    workspaceId.value = parseInt(id)
  }
  fetchWorkspaceDetail()
  loadPlans()
})
</script>

<style scoped>
.testplan-management {
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
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
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

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


.id-text {
  font-weight: 600;
  color: #409eff;
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



.action-group {
  display: flex;
  gap: 4px;
  flex-wrap: nowrap;
}

.action-btn {
  display: inline-block;
  padding: 2px 7px;
  font-size: 12px;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  line-height: 1.6;
  user-select: none;
}

.action-edit {
  color: #3182ce;
  background: #ebf8ff;
  border: 1px solid #bee3f8;
}

.action-edit:hover {
  background: #d4edfa;
  border-color: #90cdf4;
}

.action-link {
  color: #38a169;
  background: #f0fff4;
  border: 1px solid #c6f6d5;
}

.action-link:hover {
  background: #d4f5e4;
  border-color: #9ae6b4;
}

.action-run {
  color: #d69e2e;
  background: #fffff0;
  border: 1px solid #fefcbf;
}

.action-run:hover {
  background: #fef9c3;
  border-color: #fde68a;
}

.action-view {
  color: #718096;
  background: #f7fafc;
  border: 1px solid #e2e8f0;
}

.action-view:hover {
  background: #edf2f7;
  border-color: #cbd5e0;
}

.action-delete {
  color: #e53e3e;
  background: #fff5f5;
  border: 1px solid #fed7d7;
}

.action-delete:hover {
  background: #ffebeb;
  border-color: #feb2b2;
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

.execute-info {
  padding: 10px;
}

.execute-info p {
  margin: 10px 0;
  font-size: 14px;
  color: #303133;
}

.execute-info .warning {
  color: #e6a23c;
  background: #fdf6ec;
  padding: 10px;
  border-radius: 4px;
}

.device-summary {
  display: flex;
  gap: 20px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin: 12px 0;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-label {
  font-size: 13px;
  color: #606266;
}

.summary-value {
  font-size: 15px;
  font-weight: 600;
  color: #409eff;
}

.summary-item.dynamic .summary-value {
  color: #67c23a;
}

.tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 13px;
}

.tip-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.view-content {
  padding: 10px 0;
}

.view-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.view-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.info-value {
  font-size: 13px;
  color: #606266;
}

.content-box {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
}

.content-text {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.case-tabs {
  margin-top: 10px;
}

.add-case-tab,
.associated-case-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0 10px 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ml-2 {
  margin-left: 8px;
}

.case-table {
  border-radius: 8px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

:deep(.case-management-dialog .el-dialog__body) {
  padding: 15px 20px 20px;
}

/* 关联用例统计栏 */
.associated-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
  color: #64748b;
}

.stat-total strong {
  color: #3b82f6;
}

.stat-specified strong {
  color: #10b981;
}

.stat-dynamic strong {
  color: #f59e0b;
}

.stat-divider {
  color: #d1d5db;
}

/* 批量配置栏 */
.batch-config-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
  border: 1px solid #e0e7ff;
  border-radius: 10px;
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.batch-label {
  font-size: 13px;
  color: #4b5563;
  white-space: nowrap;
}

.batch-label strong {
  color: #3b82f6;
  font-size: 15px;
}

/* 已关联用例标签样式 */
.device-tag {
  background: #ecfdf5;
  color: #059669;
  border: none;
}

.dynamic-tag {
  border: none;
}

.config-text {
  font-size: 13px;
  color: #374151;
}

/* ===== 创建/编辑测试计划弹窗 ===== */
.cp-dialog .el-dialog {
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.15), 0 4px 16px rgba(0, 0, 0, 0.06);
}

.cp-dialog .el-dialog__header {
  padding: 24px 28px 0;
  margin: 0;
  border: none;
  background: #fff;
}

.cp-dialog .el-dialog__headerbtn {
  top: 18px;
  right: 18px;
}

.cp-dialog .el-dialog__body {
  padding: 20px 28px 8px;
  background: #fff;
}

.cp-dialog .el-dialog__footer {
  padding: 8px 28px 24px;
  border: none;
  background: #fff;
}

.cp-header {
  padding-bottom: 4px;
}

.cp-header-title {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.2px;
}

.cp-header-subtitle {
  font-size: 12.5px;
  color: #86868b;
  margin-top: 4px;
  line-height: 1.4;
}

.cp-form .el-form-item {
  margin-bottom: 18px;
}

.cp-form .el-form-item:last-child {
  margin-bottom: 0;
}

.cp-form .el-form-item__label {
  padding-bottom: 6px !important;
  line-height: 1.4;
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
}

.cp-form .el-input__wrapper,
.cp-form .el-textarea__inner {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #d2d2d7 inset;
  transition: box-shadow 0.15s ease, background 0.15s ease;
  background: #fafafa;
  padding: 4px 12px;
}

.cp-form .el-input__wrapper:hover,
.cp-form .el-textarea__inner:hover {
  box-shadow: 0 0 0 1px #b8b8be inset;
  background: #f5f5f7;
}

.cp-form .el-input.is-focus .el-input__wrapper,
.cp-form .el-textarea.is-focus .el-textarea__inner {
  box-shadow: 0 0 0 2px #007aff inset;
  background: #fff;
}

.cp-form .el-textarea__inner {
  padding: 8px 12px;
  line-height: 1.5;
}

.cp-form .el-input__inner {
  height: 36px;
  font-size: 14px;
}

.cp-form .el-textarea__inner::placeholder,
.cp-form .el-input__inner::placeholder {
  color: #aeaeb2;
}

.cp-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cp-footer .el-button {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 18px;
  height: auto;
  min-width: 80px;
}

.cp-footer .el-button--primary {
  background: #007aff;
  border-color: #007aff;
}

.cp-footer .el-button--primary:hover {
  background: #0062cc;
  border-color: #0062cc;
}

/* ===== 编辑用例配置弹窗 ===== */
.er-dialog .el-dialog {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12), 0 4px 14px rgba(0, 0, 0, 0.05);
}

.er-dialog .el-dialog__header {
  padding: 24px 28px 0;
  margin: 0;
  border: none;
  background: #fff;
}

.er-dialog .el-dialog__headerbtn {
  top: 20px;
  right: 20px;
}

.er-dialog .el-dialog__headerbtn .el-dialog__close {
  font-size: 18px;
  color: #9ca3af;
  transition: color 0.15s ease;
}

.er-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: #374151;
}

.er-dialog .el-dialog__body {
  padding: 16px 28px 8px;
  background: #fff;
}

.er-dialog .el-dialog__footer {
  padding: 8px 28px 24px;
  border: none;
  background: #fff;
}

/* Header with icon */
.er-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 2px;
}

.er-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #eef2ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #5b6ef7;
  font-size: 18px;
  flex-shrink: 0;
}

.er-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.er-header-title {
  font-size: 17px;
  font-weight: 600;
  color: #111827;
  letter-spacing: -0.3px;
}

.er-header-subtitle {
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.4;
}

/* 用例信息卡片 */
.er-case-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #f8f9fb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 18px;
  border-left: 2px solid #5b6ef7;
}

.er-case-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.er-case-card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  flex-shrink: 0;
}

/* 表单分组 */
.er-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 执行环境 — 蓝色主题 */
.er-group:nth-child(1) {
  border-left: 2px solid #4b8af4;
}

.er-group:nth-child(1) .er-group-title-row {
  background: #f5f9fd;
}

.er-group:nth-child(1) .er-group-icon {
  background: #e8f0fe;
  color: #4b8af4;
}

/* AI 模型 — 紫色主题 */
.er-group:nth-child(2) {
  border-left: 2px solid #7c5ce7;
}

.er-group:nth-child(2) .er-group-title-row {
  background: #f8f5fd;
}

.er-group:nth-child(2) .er-group-icon {
  background: #f0e8fe;
  color: #7c5ce7;
}

/* 推理参数 — 琥珀主题 */
.er-group:nth-child(3) {
  border-left: 2px solid #e8962e;
}

.er-group:nth-child(3) .er-group-title-row {
  background: #fefaf5;
}

.er-group:nth-child(3) .er-group-icon {
  background: #fef3e8;
  color: #e8962e;
}

.er-group {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.15s ease;
}

.er-group:hover {
  border-color: #d1d5db;
}

.er-group-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
}

.er-group-icon {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.er-group-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #374151;
  letter-spacing: 0.3px;
}

.er-group-body {
  padding: 12px 14px 4px;
}

.er-group-body--grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}

.er-form-item--full {
  grid-column: 1 / -1;
}

.er-form .el-form-item {
  margin-bottom: 14px;
}

.er-form .el-form-item:last-child {
  margin-bottom: 8px;
}

.er-form .el-form-item__label {
  padding-bottom: 6px !important;
  line-height: 1.4;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.er-field-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.er-field-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  line-height: 1.5;
}

.er-field-tag--dynamic {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.er-field-tag--specified {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.er-form .el-input__wrapper,
.er-form .el-textarea__inner {
  border-radius: 9px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  transition: box-shadow 0.15s ease, background 0.15s ease;
  background: #f9fafb;
  padding: 4px 12px;
}

.er-form .el-input__wrapper:hover,
.er-form .el-textarea__inner:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.er-form .el-input.is-focus .el-input__wrapper,
.er-form .el-textarea.is-focus .el-textarea__inner {
  box-shadow: 0 0 0 2px rgba(91, 110, 247, 0.25) inset;
  background: #fff;
}

.er-form .el-select .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px rgba(91, 110, 247, 0.25) inset;
  background: #fff;
}

.er-form .el-input__inner {
  height: 36px;
  font-size: 14px;
}

.er-form .el-textarea__inner {
  padding: 8px 12px;
}

.er-form .el-input__inner::placeholder,
.er-form .el-textarea__inner::placeholder {
  color: #9ca3af;
}

.er-field-hint {
  font-size: 11.5px;
  color: #6b7280;
  margin-top: 22px;
  line-height: 1.4;
  width: 100%;
}

/* 推理强度 - 坡度滑块 */
.er-reasoning-slider {
  padding: 8px 0 4px;
  width: 100%;
}

.er-slider-bar {
  position: relative;
  height: 32px;
  cursor: pointer;
  touch-action: none;
}

.er-slider-track {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 6px;
  transform: translateY(-50%);
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.er-slider-fill {
  height: 100%;
  background: linear-gradient(90deg, #4b8af4, #7c5ce7, #e8962e);
  transition: width 0.2s ease;
}

.er-slider-stop {
  position: absolute;
  top: 50%;
  transform: translateY(-50%) translateX(-50%);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
}

.er-slider-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #d1d5db;
  transition: all 0.15s ease;
  box-sizing: border-box;
  flex-shrink: 0;
}

.er-slider-stop.active .er-slider-dot {
  width: 16px;
  height: 16px;
  border-width: 3px;
  border-color: #5b6ef7;
  box-shadow: 0 0 0 3px rgba(91, 110, 247, 0.18);
}

.er-slider-labels {
  position: relative;
  height: 52px;
  margin-top: 8px;
}

.er-slider-label {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.15s ease;
  min-width: 48px;
}

.er-slider-label:hover {
  background: #f3f4f6;
}

.er-slider-label-text {
  font-size: 13px;
  font-weight: 500;
  color: #4b5563;
  transition: color 0.15s ease;
}

.er-slider-label.active .er-slider-label-text {
  color: #5b6ef7;
  font-weight: 600;
}

.er-slider-label-sub {
  font-size: 10px;
  color: #9ca3af;
  transition: color 0.15s ease;
}

.er-slider-label.active .er-slider-label-sub {
  color: #6b7280;
}

/* Footer */
.er-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.er-footer .el-button {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 18px;
  height: auto;
  min-width: 80px;
}
</style>
