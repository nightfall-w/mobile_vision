<template>
  <div class="testcase-management">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">用例管理</h1>
          <p class="page-subtitle">管理工作空间下的自然语言用例</p>
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
          v-model="searchForm.case_name"
          placeholder="搜索用例名称"
          class="search-input"
          @keyup.enter="fetchCases"
        >
          <template #prefix>
            <el-icon><Search/></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="searchForm.status"
          placeholder="选择状态"
          class="search-select"
        >
          <el-option label="全部" value="" />
          <el-option label="调试中" value="debugging" />
          <el-option label="已完成" value="completed" />
          <el-option label="禁用" value="disabled" />
        </el-select>
        <el-select
          v-model="searchForm.level"
          placeholder="选择等级"
          class="search-select"
        >
          <el-option label="全部" value="" />
          <el-option label="P0" value="P0" />
          <el-option label="P1" value="P1" />
          <el-option label="P2" value="P2" />
          <el-option label="P3" value="P3" />
        </el-select>
        <el-button @click="fetchCases" class="search-btn">
          <el-icon><Search/></el-icon>
          查询
        </el-button>
        <el-button @click="resetSearch" class="reset-btn">
          <el-icon><Refresh/></el-icon>
          重置
        </el-button>
        <el-button type="primary" @click="goToCreate" style="margin-left: auto">
          <el-icon :size="16" class="mr-1"><Plus/></el-icon>
          新建用例
        </el-button>
      </div>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
      <div class="table-container">
        <el-table
        :data="cases"
        v-loading="loading"
        element-loading-text="加载中..."
        style="width: 100%"
        :cell-style="{ textAlign: 'center' }"
        :header-cell-style="{ textAlign: 'center', backgroundColor: '#f5f7fa', color: '#606266' }"
        border
        empty-text="暂无用例数据"
        :height="tableHeight"
      >
        <el-table-column label="用例ID" width="100">
          <template #default="{ row }">
            <span class="id-text">#{{ row.case_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="case_name" label="用例名称" min-width="200" />
        <el-table-column prop="updater_name" label="更新人" width="120" />
        <el-table-column prop="level_display" label="等级" width="100">
          <template #default="{ row }">
            <el-tag
              :type="getLevelTagType(row.level)"
              size="small"
              effect="dark"
            >
              {{ row.level_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_display" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="getStatusTagType(row.status)"
              size="small"
              effect="dark"
            >
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="update_time" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.update_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <span class="action-btn action-view" @click="openViewDialog(row)">详情</span>
              <span class="action-btn action-edit" @click="goToEdit(row.case_id)">编辑</span>
              <span class="action-btn action-delete" @click="openDeleteDialog(row)">删除</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="table-footer">
        <el-pagination
          :current-page="pagination.page_num"
          :page-size="pagination.page_size"
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
      v-model="viewDialogVisible"
      width="800px"
      :close-on-click-modal="false"
      class="tc-detail-dialog"
    >
      <template #header>
        <div class="tc-detail-header">
          <span class="tc-detail-header-icon"><el-icon><Document /></el-icon></span>
          <div>
            <h2 class="tc-detail-header-title">用例详情</h2>
            <p class="tc-detail-header-desc">查看测试用例的完整信息</p>
          </div>
        </div>
      </template>
      <div v-if="viewCase" class="tc-detail-body">
        <!-- 基本信息 -->
        <div class="tc-detail-section">
          <div class="tc-detail-section-header">
            <span class="tc-detail-section-icon tc-section-icon--info"><el-icon><InfoFilled /></el-icon></span>
            <h3 class="tc-detail-section-title">基本信息</h3>
          </div>
          <div class="tc-detail-section-body">
            <div class="tc-detail-grid">
              <div class="tc-detail-item">
                <span class="tc-detail-label">用例名称</span>
                <span class="tc-detail-value">{{ viewCase.case_name }}</span>
              </div>
              <div class="tc-detail-item">
                <span class="tc-detail-label">等级</span>
                <span class="tc-detail-badge" :class="'tc-badge--level-' + viewCase.level.toLowerCase()">{{ viewCase.level_display }}</span>
              </div>
              <div class="tc-detail-item">
                <span class="tc-detail-label">状态</span>
                <span class="tc-detail-badge" :class="'tc-badge--status-' + viewCase.status">{{ viewCase.status_display }}</span>
              </div>
              <div class="tc-detail-item">
                <span class="tc-detail-label">更新人</span>
                <span class="tc-detail-value">{{ viewCase.updater_name }}</span>
              </div>
              <div class="tc-detail-item">
                <span class="tc-detail-label">创建时间</span>
                <span class="tc-detail-value">{{ formatTime(viewCase.create_time) }}</span>
              </div>
              <div class="tc-detail-item">
                <span class="tc-detail-label">更新时间</span>
                <span class="tc-detail-value">{{ formatTime(viewCase.update_time) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 测试任务正文 -->
        <div class="tc-detail-section">
          <div class="tc-detail-section-header">
            <span class="tc-detail-section-icon tc-section-icon--content"><el-icon><Edit /></el-icon></span>
            <h3 class="tc-detail-section-title">测试任务正文</h3>
          </div>
          <div class="tc-detail-section-body">
            <div class="tc-detail-content-box">
              <pre class="tc-detail-content-text">{{ viewCase.content || '无' }}</pre>
            </div>
          </div>
        </div>

        <!-- APP使用说明 -->
        <div class="tc-detail-section">
          <div class="tc-detail-section-header">
            <span class="tc-detail-section-icon tc-section-icon--usage"><el-icon><Document /></el-icon></span>
            <h3 class="tc-detail-section-title">APP使用说明</h3>
          </div>
          <div class="tc-detail-section-body">
            <div class="tc-detail-content-box">
              <pre class="tc-detail-content-text">{{ viewCase.usage_instructions || '无' }}</pre>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end">
          <el-button @click="viewDialogVisible = false">关闭</el-button>
        </div>
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
        <p class="text-gray-700">确定要删除用例 <strong>{{ deleteCaseName }}</strong> 吗？</p>
        <p class="text-gray-500 text-sm mt-2">此操作不可撤销，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="deleteDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="deleteCase">确定删除</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Search, Refresh, Edit, Delete, Warning, InfoFilled, User, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { deleteTestCase, getTestCaseList, getTestCaseDetail, getWorkspaceDetail } from '@/network/api.js'

export default {
  name: 'TestCaseManagement',
  components: {
    Plus,
    Search,
    Refresh,
    Edit,
    Delete,
    Warning,
    InfoFilled,
    User,
    Document
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const workspaceId = route.params.id

    const cases = ref([])
    const total = ref(0)
    const loading = ref(false)

    const pagination = reactive({
      page_num: 1,
      page_size: 10
    })

    const searchForm = reactive({
      case_name: '',
      status: '',
      level: ''
    })

    const deleteDialogVisible = ref(false)
    const deleteCaseId = ref(null)
    const deleteCaseName = ref('')

    const viewDialogVisible = ref(false)
    const viewCase = ref(null)

    const workspaceName = ref('')
    const managers = ref([])
    const managerNames = computed(() => managers.value.map(m => m.nickname).join('、'))

    const tableHeight = computed(() => {
      return window.innerHeight - 320
    })

    const fetchWorkspaceDetail = async () => {
      try {
        const res = await getWorkspaceDetail({ workspace_id: parseInt(workspaceId) })
        if (res.code === 0) {
          workspaceName.value = res.data.workspace_name
          managers.value = res.data.manager || []
        }
      } catch (error) {
        console.error('获取工作空间详情失败:', error)
      }
    }

    const fetchCases = async () => {
      loading.value = true
      try {
        const res = await getTestCaseList({
          workspace_id: parseInt(workspaceId),
          case_name: searchForm.case_name || undefined,
          status: searchForm.status || undefined,
          level: searchForm.level || undefined,
          page_num: pagination.page_num,
          page_size: pagination.page_size
        })

        if (res.code === 0) {
          cases.value = res.data.cases
          total.value = res.data.total
        } else {
          console.error('获取用例列表失败:', res.message)
        }
      } catch (error) {
        console.error('获取用例列表失败:', error)
      } finally {
        loading.value = false
      }
    }

    const handlePageChange = (page) => {
      pagination.page_num = page
      fetchCases()
    }

    const handleSizeChange = (size) => {
      pagination.page_size = size
      pagination.page_num = 1
      fetchCases()
    }

    const resetSearch = () => {
      searchForm.case_name = ''
      searchForm.status = ''
      searchForm.level = ''
      pagination.page_num = 1
      fetchCases()
    }

    const goToCreate = () => {
      router.push(`/workspace/${workspaceId}/testcases/create`)
    }

    const goToEdit = (caseId) => {
      router.push(`/workspace/${workspaceId}/testcases/${caseId}/edit`)
    }

    const openViewDialog = async (row) => {
      try {
        const res = await getTestCaseDetail(row.case_id)
        if (res.code === 0) {
          viewCase.value = {
            ...res.data,
            updater_name: row.updater_name
          }
          viewDialogVisible.value = true
        }
      } catch (error) {
        console.error('获取用例详情失败:', error)
      }
    }

    const openDeleteDialog = (row) => {
      deleteCaseId.value = row.case_id
      deleteCaseName.value = row.case_name
      deleteDialogVisible.value = true
    }

    const deleteCase = async () => {
      try {
        const res = await deleteTestCase(deleteCaseId.value)
        if (res.code === 0) {
          ElMessage.success('删除成功')
          deleteDialogVisible.value = false
          fetchCases()
        } else {
          ElMessage.error(res.message || '删除失败')
        }
      } catch (error) {
        console.error('删除用例失败:', error)
        ElMessage.error('删除失败：网络或服务器错误')
      }
    }

    const getLevelTagType = (level) => {
      const types = {
        'P0': 'danger',
        'P1': 'warning',
        'P2': 'info',
        'P3': 'success'
      }
      return types[level] || 'info'
    }

    const getStatusTagType = (status) => {
      const types = {
        'debugging': 'warning',
        'completed': 'success',
        'disabled': 'info'
      }
      return types[status] || 'info'
    }

    const formatTime = (timeString) => {
      if (!timeString) return ''
      return timeString.replace('T', ' ')
    }

    onMounted(() => {
      fetchWorkspaceDetail()
      fetchCases()
    })

    return {
      cases,
      total,
      loading,
      pagination,
      searchForm,
      deleteDialogVisible,
      deleteCaseName,
      viewDialogVisible,
      workspaceName,
      managers,
      managerNames,
      viewCase,
      tableHeight,
      fetchCases,
      handlePageChange,
      handleSizeChange,
      resetSearch,
      goToCreate,
      goToEdit,
      openViewDialog,
      openDeleteDialog,
      deleteCase,
      getLevelTagType,
      getStatusTagType,
      formatTime
    }
  }
}
</script>

<style scoped>
.testcase-management {
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

:deep(.el-table .el-table__cell) {
  padding: 10px 0;
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

.id-text {
  font-weight: 600;
  color: #409eff;
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

/* ===== 用例详情弹窗 ===== */
.tc-detail-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.tc-detail-dialog :deep(.el-dialog__body) {
  padding: 0 24px 20px;
}

.tc-detail-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.tc-detail-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}

.tc-detail-header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.tc-detail-header-desc {
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #9ca3af;
}

.tc-detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 0 4px;
}

.tc-detail-section {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  border-left: 2px solid #5b6ef7;
}

.tc-detail-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f5f7fd;
  border-bottom: 1px solid #e5e7eb;
}

.tc-detail-section-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.tc-section-icon--info {
  background: #e8f0fe;
  color: #4b8af4;
}

.tc-section-icon--content {
  background: #f0e8fe;
  color: #7c5ce7;
}

.tc-section-icon--usage {
  background: #fef3e8;
  color: #e8962e;
}

.tc-detail-section-title {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: #1f2937;
}

.tc-detail-section-body {
  padding: 16px;
}

.tc-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}

.tc-detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tc-detail-label {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
}

.tc-detail-value {
  font-size: 13.5px;
  color: #1f2937;
}

.tc-detail-content-box {
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px 16px;
  max-height: 260px;
  overflow-y: auto;
}

.tc-detail-content-text {
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13.5px;
  line-height: 1.65;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== SwiftUI Badges ===== */
.tc-detail-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  letter-spacing: 0.2px;
  width: fit-content;
}

.tc-badge--level-p0 {
  background: #fde8e8;
  color: #c53030;
}

.tc-badge--level-p1 {
  background: #fef3cd;
  color: #b7791f;
}

.tc-badge--level-p2 {
  background: #e8edf3;
  color: #4a5568;
}

.tc-badge--level-p3 {
  background: #e6f7e6;
  color: #276749;
}

.tc-badge--status-debugging {
  background: #fef3cd;
  color: #b7791f;
}

.tc-badge--status-completed {
  background: #e6f7e6;
  color: #276749;
}

.tc-badge--status-disabled {
  background: #e8edf3;
  color: #a0aec0;
}
</style>
