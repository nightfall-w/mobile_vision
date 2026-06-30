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
    <el-dialog
      :title="dialogTitle"
      v-model="dialogVisible"
      width="500px"
    >
      <el-form :model="formData" label-width="120px">
        <el-form-item label="模型名称" prop="model">
          <el-input
            v-model="formData.model"
            placeholder="请输入模型名称"
            size="small"
          />
        </el-form-item>
        <el-form-item label="API密钥" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="请输入API密钥"
            size="small"
            show-password
          />
        </el-form-item>
        <el-form-item label="基础URL" prop="base_url">
          <el-input
            v-model="formData.base_url"
            placeholder="请输入基础URL"
            size="small"
          />
        </el-form-item>
        <el-form-item label="协议类型" prop="api_protocol">
          <el-select
            v-model="formData.api_protocol"
            placeholder="请选择协议类型"
            size="small"
          >
            <el-option label="OpenAI" value="OpenAI" />
            <el-option label="Anthropic" value="Anthropic" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属级别" prop="workspace_id">
          <el-select
            v-model="formData.workspace_id"
            placeholder="请选择级别"
            size="small"
          >
            <el-option label="系统级别" value="__system__" />
            <el-option
              v-for="workspace in workspaces"
              :key="workspace.workspace_id"
              :label="workspace.workspace_name"
              :value="String(workspace.workspace_id)"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch
            v-model="formData.is_active"
            active-text="启用"
            inactive-text="禁用"
            active-color="#165DFF"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button size="small" @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          size="small"
          @click="handleSave"
          :loading="saving"
        >
          {{ saving ? '保存中...' : '保存' }}
        </el-button>
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
import { Plus, Refresh, Search, Warning } from '@element-plus/icons-vue';
import { getMyManageWorkspaces } from '@/network/api.js';
import { createLLMCredential, getLLMCredentialList, updateLLMCredential, deleteLLMCredential, getLLMCredentialWithKey } from '@/network/api.js';

const credentials = ref([]);
const workspaces = ref([]);
const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const dialogTitle = ref('添加凭证');
const showApiKey = ref(false);
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
  showApiKey.value = false;
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
      showApiKey.value = false;
      setTimeout(() => {
        dialogVisible.value = true;
      }, 0);
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
</style>
