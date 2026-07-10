<template>
  <div class="llm-credential">
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
              <h1 class="text-xl font-bold text-gray-800 mb-1">LLM凭证管理</h1>
              <p class="text-sm text-gray-600">管理系统和工作空间级别的LLM凭证配置</p>
            </div>

            <div class="flex flex-wrap gap-2">
              <el-button
                type="primary"
                @click="openCreateDialog"
                class="text-sm px-4"
              >
                <el-icon class="mr-1" :size="14">
                  <Plus/>
                </el-icon>
                添加凭证
              </el-button>
              <el-button
                @click="loadCredentials"
                class="text-sm px-4"
              >
                <el-icon class="mr-1" :size="14">
                  <Refresh/>
                </el-icon>
                刷新列表
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 筛选区域卡片 -->
      <el-card class="filter-card rounded-xl shadow-md border-0 bg-white">
        <div class="flex flex-wrap items-center gap-4 p-4">
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600">所属级别:</label>
            <el-select
              v-model="filterLevel"
              placeholder="全部"
              class="w-36"
              size="default"
            >
              <el-option label="全部" :value="''" />
              <el-option label="系统级别" :value="'system'" />
              <el-option label="工作空间级别" :value="'workspace'" />
            </el-select>
          </div>
          <div v-if="filterLevel === 'workspace'" class="flex items-center gap-2">
            <label class="text-sm text-gray-600">选择工作空间:</label>
            <el-select
              v-model="filterWorkspaceId"
              placeholder="请选择"
              class="w-44"
              size="default"
            >
              <el-option
                v-for="workspace in workspaces"
                :key="workspace.workspace_id"
                :label="workspace.workspace_name"
                :value="workspace.workspace_id"
              />
            </el-select>
          </div>
          <el-button
            type="primary"
            @click="handleSearch"
          >
            <el-icon :size="14"><Search/></el-icon> 查询
          </el-button>
        </div>
      </el-card>
    </div>
    <div class="scroll-content">
      <!-- 凭证列表卡片 -->
      <el-card class="table-card rounded-xl shadow-md border-0 bg-white overflow-hidden">
        <div class="table-container">
          <el-table
            :data="credentials"
            v-loading="loading"
            element-loading-text="加载中..."
            style="width: 100%"
            :height="tableHeight"
            :cell-style="{ textAlign: 'center' }"
            :header-cell-style="{ textAlign: 'center', backgroundColor: '#f5f7fa', color: '#606266' }"
            border
            empty-text="暂无凭证"
          >
            <el-table-column label="ID" width="80">
              <template #default="{ row }">
                <span class="id-text">#{{ row.id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="model" label="模型名称" min-width="150">
              <template #default="{ row }">
                <span class="text-sm text-gray-800">{{ row.model }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="api_key" label="API密钥" width="120">
              <template #default="{ row }">
                <span class="text-xs text-gray-500">******</span>
              </template>
            </el-table-column>
            <el-table-column prop="base_url" label="基础URL" min-width="200">
              <template #default="{ row }">
                <el-tooltip :content="row.base_url" placement="top">
                  <span class="text-xs text-gray-600 truncate">{{ row.base_url }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="api_protocol" label="协议类型" width="120">
              <template #default="{ row }">
                <el-tag
                  :type="row.api_protocol === 'openai' ? 'primary' : 'success'"
                  size="small"
                  effect="dark"
                >
                  {{ row.api_protocol }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="所属级别" width="120">
              <template #default="{ row }">
                <el-tag
                  :type="row.workspace_id ? 'warning' : 'success'"
                  size="small"
                  effect="dark"
                >
                  {{ row.workspace_id ? '工作空间' : '系统级别' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.is_active ? 'success' : 'info'"
                  size="small"
                  effect="dark"
                >
                  {{ row.is_active ? '已启用' : '已禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button type="info" size="small" @click="openEditDialog(row)">编辑</el-button>
                  <el-button type="danger" size="small" @click="confirmDelete(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <div class="table-footer">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
          background
        />
      </div>
    </div>

    <!-- 添加/编辑凭证弹窗 -->
    <el-dialog v-model="dialogVisible" width="520px" :close-on-click-modal="false" class="lc-dialog">
      <template #header>
        <div class="lc-header">
          <span class="lc-header-icon"><el-icon :size="20"><Key/></el-icon></span>
          <div>
            <h2 class="lc-header-title">{{ dialogTitle }}</h2>
            <p class="lc-header-desc">{{ dialogTitle === '添加凭证' ? '添加新的 LLM 凭证配置' : '修改已有的 LLM 凭证信息' }}</p>
          </div>
        </div>
      </template>
      <div class="lc-body">
        <div class="lc-section">
          <div class="lc-section-header">
            <span class="lc-section-icon"><el-icon><InfoFilled/></el-icon></span>
            <h3 class="lc-section-title">凭证信息</h3>
          </div>
          <div class="lc-section-body">
            <div class="lc-field">
              <label class="lc-label">模型名称 <span class="lc-required">*</span></label>
              <el-input v-model="formData.model" placeholder="例如：gpt-4o" clearable class="lc-input" />
            </div>
            <div class="lc-field">
              <label class="lc-label">API密钥 <span class="lc-required">*</span></label>
              <el-input v-model="formData.api_key" type="password" placeholder="请输入API密钥" show-password clearable class="lc-input" />
            </div>
            <div class="lc-field">
              <label class="lc-label">基础URL <span class="lc-required">*</span></label>
              <el-input v-model="formData.base_url" placeholder="例如：https://api.openai.com/v1" clearable class="lc-input" />
            </div>
            <div class="lc-field">
              <label class="lc-label">协议类型</label>
              <el-select v-model="formData.api_protocol" class="lc-select">
                <el-option label="OpenAI" value="OpenAI" />
                <el-option label="Anthropic" value="Anthropic" />
              </el-select>
            </div>
          </div>
        </div>
        <div class="lc-section lc-section--amber">
          <div class="lc-section-header">
            <span class="lc-section-icon lc-section-icon--amber"><el-icon><Setting/></el-icon></span>
            <h3 class="lc-section-title">所属配置</h3>
          </div>
          <div class="lc-section-body">
            <div class="lc-field">
              <label class="lc-label">所属级别</label>
              <el-select v-model="formData.workspace_id" class="lc-select">
                <el-option label="系统级别" value="__system__" />
                <el-option v-for="workspace in workspaces" :key="workspace.workspace_id" :label="workspace.workspace_name" :value="String(workspace.workspace_id)" />
              </el-select>
            </div>
            <div class="lc-field lc-field--switch">
              <label class="lc-label">状态</label>
              <el-switch v-model="formData.is_active" active-text="启用" inactive-text="禁用" active-color="#5b6ef7" />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="lc-footer">
          <el-button @click="dialogVisible = false" class="lc-btn-cancel">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving" class="lc-btn-primary">{{ saving ? '保存中...' : '保存' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 删除确认弹窗 -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="确认删除"
      width="400px"
      :close-on-click-modal="false"
    >
      <div class="text-center py-4">
        <el-icon :size="48" class="text-red-500 mb-4"><Warning/></el-icon>
        <p class="text-gray-700">确定要删除凭证 <strong>{{ deleteRow?.model }}</strong> 吗？</p>
        <p class="text-gray-500 text-sm mt-2">此操作不可撤销，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button @click="deleteDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="doDelete">确定删除</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Refresh, Search, Warning, Key, InfoFilled, Setting } from '@element-plus/icons-vue';
import { getMyManageWorkspaces } from '@/network/api.js';
import { createLLMCredential, getLLMCredentialList, updateLLMCredential, deleteLLMCredential, getLLMCredentialWithKey } from '@/network/api.js';

const credentials = ref([]);
const workspaces = ref([]);
const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const dialogTitle = ref('添加凭证');
const filterLevel = ref('');
const filterWorkspaceId = ref(null);
const deleteDialogVisible = ref(false);
const deleteRow = ref(null);

// 分页参数
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

const formData = ref({
  id: null,
  model: '',
  api_key: '',
  base_url: '',
  api_protocol: 'OpenAI',
  workspace_id: null,
  is_active: true
});

watch(filterLevel, () => {
  if (filterLevel.value !== 'workspace') {
    filterWorkspaceId.value = null;
  }
});

const loadWorkspaces = async () => {
  try {
    const resp = await getMyManageWorkspaces({ page_num: 1, page_size: 100 });
    if (resp.code === 0) {
      workspaces.value = resp.data.workspaces;
    }
  } catch (error) {
    console.error('加载工作空间失败:', error);
  }
};

const loadCredentials = async (page = 1, size = 20) => {
  loading.value = true;
  try {
    const params = {
      page_num: page,
      page_size: size
    };
    if (filterLevel.value === 'system') {
      params.workspace_id = 'system';
    } else if (filterLevel.value === 'workspace' && filterWorkspaceId.value) {
      params.workspace_id = filterWorkspaceId.value;
    }
    const resp = await getLLMCredentialList(params);
    if (resp.code === 0) {
      credentials.value = resp.data.list;
      total.value = resp.data.total;
    }
  } catch (error) {
    console.error('加载凭证列表失败:', error);
    ElMessage.error('加载凭证列表失败');
  } finally {
    loading.value = false;
  }
};

const handlePageChange = (page) => {
  currentPage.value = page;
  loadCredentials(page, pageSize.value);
};

const handleSizeChange = (size) => {
  pageSize.value = size;
  currentPage.value = 1;
  loadCredentials(1, size);
};

const handleSearch = () => {
  currentPage.value = 1;
  loadCredentials(1, pageSize.value);
};

const openCreateDialog = () => {
  dialogTitle.value = '添加凭证';
  formData.value = {
    id: null,
    model: '',
    api_key: '',
    base_url: '',
    api_protocol: 'OpenAI',
    workspace_id: null,
    is_active: true
  };
  dialogVisible.value = true;
};

const openEditDialog = async (row) => {
  dialogTitle.value = '编辑凭证';
  try {
    const resp = await getLLMCredentialWithKey(row.id);
    if (resp.code === 0) {
      const workspaceId = resp.data.workspace_id;
      formData.value = {
        id: resp.data.id,
        model: resp.data.model,
        api_key: '',
        base_url: resp.data.base_url,
        api_protocol: resp.data.api_protocol,
        workspace_id: workspaceId === null || workspaceId === undefined ? '__system__' : String(workspaceId),
        is_active: resp.data.is_active
      };
      dialogVisible.value = true;
    } else {
      ElMessage.error('获取凭证详情失败');
    }
  } catch (error) {
    console.error('获取凭证详情失败:', error);
    ElMessage.error('获取凭证详情失败');
  }
};

const confirmDelete = (row) => {
  deleteRow.value = row;
  deleteDialogVisible.value = true;
};

const doDelete = async () => {
  if (!deleteRow.value) return;
  try {
    const resp = await deleteLLMCredential(deleteRow.value.id);
    if (resp.code === 0) {
      ElMessage.success('删除成功');
      deleteDialogVisible.value = false;
      deleteRow.value = null;
      loadCredentials();
    } else {
      ElMessage.error(resp.msg || '删除失败');
    }
  } catch (error) {
    console.error('删除凭证失败:', error);
    ElMessage.error('删除凭证失败');
  }
};

const handleSave = async () => {
  if (!formData.value.model) {
    ElMessage.warning('请输入模型名称');
    return;
  }
  if (!formData.value.api_key) {
    ElMessage.warning('请输入API密钥');
    return;
  }
  if (!formData.value.base_url) {
    ElMessage.warning('请输入基础URL');
    return;
  }

  saving.value = true;
  try {
    let workspaceId = formData.value.workspace_id;
    if (workspaceId === '__system__') {
      workspaceId = null;
    }
    const submitData = {
      ...formData.value,
      workspace_id: workspaceId
    };
    let resp;
    if (formData.value.id) {
      resp = await updateLLMCredential(submitData);
    } else {
      resp = await createLLMCredential(submitData);
    }
    if (resp.code === 0) {
      ElMessage.success(formData.value.id ? '更新成功' : '创建成功');
      dialogVisible.value = false;
      loadCredentials();
    } else {
      ElMessage.error(resp.msg || '保存失败');
    }
  } catch (error) {
    console.error('保存凭证失败:', error);
    ElMessage.error('保存凭证失败');
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  loadWorkspaces();
  loadCredentials();
});
</script>

<style scoped>
.llm-credential {
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
  font-size: 18px;
  font-weight: 600;
  color: #1f2d3d;
}

.page-header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #646a73;
}

.id-text {
  font-weight: 600;
  color: #409eff;
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
  padding: 16px;
}

.table-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px 20px;
  margin-top: 10px;
  background-color: white;
}

/* ===== 添加/编辑凭证弹窗 ===== */
.lc-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.lc-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.lc-dialog :deep(.el-dialog__footer) {
  padding: 0;
}

.lc-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 24px 24px 0;
}

.lc-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #e8f0fe;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b8af4;
  flex-shrink: 0;
}

.lc-header-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.lc-header-desc {
  margin: 2px 0 0;
  font-size: 13px;
  color: #8e8e93;
}

.lc-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.lc-section {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  border-left: 2px solid #4b8af4;
  overflow: hidden;
}

.lc-section--amber {
  border-left-color: #e8962e;
}

.lc-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f5f7fd;
  border-bottom: 1px solid #e5e7eb;
}

.lc-section--amber .lc-section-header {
  background: #fef8f0;
}

.lc-section-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #e8f0fe;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b8af4;
  font-size: 14px;
  flex-shrink: 0;
}

.lc-section-icon--amber {
  background: #fef3e8;
  color: #e8962e;
}

.lc-section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.lc-section-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.lc-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.lc-field--switch {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.lc-field--switch .lc-label {
  margin-bottom: 0;
}

.lc-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.lc-required {
  color: #dc2626;
}

.lc-input .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.lc-input .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.lc-input .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.lc-input .el-input__inner {
  height: 38px;
  font-size: 14px;
}

.lc-select {
  width: 100%;
}

.lc-select .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.lc-select .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.lc-select .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.lc-select .el-input__inner {
  height: 38px;
  font-size: 14px;
}

.lc-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.lc-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 20px;
}

.lc-btn-primary {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 22px;
  background: #5b6ef7;
  border-color: #5b6ef7;
  box-shadow: 0 1px 3px rgba(91, 110, 247, 0.3);
  transition: all 0.15s ease;
}

.lc-btn-primary:hover {
  background: #4c5fd8;
  border-color: #4c5fd8;
  box-shadow: 0 2px 6px rgba(91, 110, 247, 0.4);
}
</style>
