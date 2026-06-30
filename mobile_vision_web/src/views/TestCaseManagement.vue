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
              v-for="manager in managers"
              :key="manager.username"
              size="small"
              class="manager-tag"
            >
              <el-icon class="mr-1" :size="12"><User/></el-icon>
              管理员：{{ manager.nickname }}
            </el-tag>
          </div>
          <el-button
            type="primary"
            @click="goToCreate"
            class="create-button"
          >
            <el-icon :size="16" class="mr-1"><Plus/></el-icon>
            新建用例
          </el-button>
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
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                type="info"
                size="small"
                @click="openViewDialog(row)"
                class="view-btn"
              >
                详情
              </el-button>
              <el-button
                type="primary"
                size="small"
                @click="goToEdit(row.case_id)"
                class="edit-btn"
              >
                编辑
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="openDeleteDialog(row)"
                class="delete-btn"
              >
                删除
              </el-button>
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
      title="用例详情"
      width="800px"
      :close-on-click-modal="false"
    >
      <div v-if="viewCase" class="view-content">
        <div class="view-section">
          <h3 class="section-title">基本信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">用例名称</span>
              <span class="info-value">{{ viewCase.case_name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">等级</span>
              <el-tag :type="getLevelTagType(viewCase.level)" size="small">
                {{ viewCase.level_display }}
              </el-tag>
            </div>
            <div class="info-item">
              <span class="info-label">状态</span>
              <el-tag :type="getStatusTagType(viewCase.status)" size="small">
                {{ viewCase.status_display }}
              </el-tag>
            </div>
            <div class="info-item">
              <span class="info-label">更新人</span>
              <span class="info-value">{{ viewCase.updater_name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ formatTime(viewCase.create_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">更新时间</span>
              <span class="info-value">{{ formatTime(viewCase.update_time) }}</span>
            </div>
          </div>
        </div>

        <div class="view-section">
          <h3 class="section-title">测试任务正文</h3>
          <div class="content-box">
            <pre class="content-text">{{ viewCase.content || '无' }}</pre>
          </div>
        </div>

        <div class="view-section">
          <h3 class="section-title">APP使用说明</h3>
          <div class="content-box">
            <pre class="content-text">{{ viewCase.usage_instructions || '无' }}</pre>
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
import { Plus, Search, Refresh, Edit, Delete, Warning, InfoFilled, User } from '@element-plus/icons-vue'
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
    User
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

.create-button {
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

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.action-buttons .el-button {
  padding: 6px 12px;
  border: none;
}

.id-text {
  font-weight: 600;
  color: #409eff;
}

.view-btn {
  color: #409eff;
  background: transparent;
}

.view-btn:hover {
  background: rgba(64, 158, 255, 0.1);
}

.edit-btn {
  color: #409eff;
  background: transparent;
}

.edit-btn:hover {
  background: rgba(64, 158, 255, 0.1);
}

.delete-btn {
  color: #f56c6c;
  background: transparent;
}

.delete-btn:hover {
  background: rgba(245, 108, 108, 0.1);
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
  max-height: 300px;
  overflow-y: auto;
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

.truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
