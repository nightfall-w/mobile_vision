<template>
  <div class="lc-page">
    <div class="lc-sticky">
      <!-- Header -->
      <div class="lc-header-card">
        <div class="lc-header-inner">
          <div class="lc-header-left">
            <div class="lc-title-group">
              <div class="lc-icon-wrap"><el-icon :size="18"><Key /></el-icon></div>
              <div>
                <h1 class="lc-title">LLM 凭证管理</h1>
                <p class="lc-subtitle">管理系统和工作空间级别的 LLM 凭证配置</p>
              </div>
            </div>
          </div>
          <div class="lc-header-actions">
            <el-button class="lc-btn lc-btn-primary" @click="openCreateDialog">
              <el-icon :size="14"><Plus /></el-icon> 添加凭证
            </el-button>
            <el-button class="lc-btn lc-btn-ghost" @click="loadCredentials()">
              <el-icon :size="14"><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </div>

      <!-- Filter -->
      <div class="lc-filter-card">
        <div class="lc-filter-inner">
          <div class="lc-filter-group">
            <span class="lc-filter-label">级别</span>
            <el-select v-model="filterLevel" placeholder="全部" class="lc-select-sm">
              <el-option label="全部" :value="''" />
              <el-option label="系统级别" :value="'system'" />
              <el-option label="工作空间" :value="'workspace'" />
            </el-select>
          </div>
          <div v-if="filterLevel === 'workspace'" class="lc-filter-group">
            <span class="lc-filter-label">工作空间</span>
            <el-select v-model="filterWorkspaceId" placeholder="选择" class="lc-select-sm">
              <el-option v-for="ws in workspaces" :key="ws.workspace_id" :label="ws.workspace_name" :value="ws.workspace_id" />
            </el-select>
          </div>
          <button class="lc-filter-btn" @click="handleSearch">
            <el-icon :size="13"><Search /></el-icon> 查询
          </button>
        </div>
      </div>
    </div>

    <div class="lc-scroll">
      <!-- Table -->
      <div class="lc-table-wrap">
        <el-table
          :data="credentials"
          v-loading="loading"
          style="width: 100%"
          :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
          :cell-style="{ textAlign: 'center' }"
          stripe
          empty-text="暂无凭证"
          height="100%"
        >
          <el-table-column label="ID" width="70">
            <template #default="{ row }"><span class="lc-id">#{{ row.id }}</span></template>
          </el-table-column>
          <el-table-column prop="model" label="模型名称" min-width="140">
            <template #default="{ row }"><span class="lc-model">{{ row.model }}</span></template>
          </el-table-column>
          <el-table-column prop="base_url" label="基础 URL" min-width="180">
            <template #default="{ row }">
              <el-tooltip :content="row.base_url" placement="top">
                <span class="lc-url">{{ row.base_url }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="api_protocol" label="协议" width="110">
            <template #default="{ row }">
              <el-tag :type="row.api_protocol === 'openai' ? 'primary' : 'success'" size="small" effect="plain" round>
                {{ row.api_protocol }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="row.workspace_id ? 'warning' : 'success'" size="small" effect="plain" round>
                {{ row.workspace_id ? '工作空间' : '系统' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="85">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="plain" round>
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新人" width="100">
            <template #default="{ row }"><span class="lc-user">{{ row.update_user_nickname || row.update_user || '-' }}</span></template>
          </el-table-column>
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }"><span class="lc-time">{{ formatTime(row.update_time) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <div class="lc-actions">
                <button class="lc-act lc-act-edit" @click="openEditDialog(row)">编辑</button>
                <button class="lc-act lc-act-del" @click="confirmDelete(row)">删除</button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Pagination (fixed bottom) -->
    <div class="lc-page-footer">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        background
        small
      />
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="dialogVisible" width="500px" :close-on-click-modal="false" class="lc-dialog" top="8vh">
      <template #header>
        <div class="lc-dlg-hd">
          <div class="lc-dlg-icon"><el-icon :size="18"><Key /></el-icon></div>
          <div>
            <div class="lc-dlg-title">{{ dialogTitle }}</div>
            <div class="lc-dlg-desc">{{ dialogTitle === '添加凭证' ? '添加新的 LLM 凭证配置' : '修改已有的 LLM 凭证信息' }}</div>
          </div>
        </div>
      </template>
      <div class="lc-dlg-body">
        <div class="lc-dlg-section">
          <div class="lc-dlg-s-hd"><el-icon :size="13"><InfoFilled /></el-icon> 凭证信息</div>
          <div class="lc-dlg-s-bd">
            <div class="lc-fld">
              <label>模型名称 <span class="lc-req">*</span></label>
              <el-input v-model="formData.model" placeholder="例如 gpt-4o" clearable />
            </div>
            <div class="lc-fld">
              <label>API 密钥 <span class="lc-req">*</span></label>
              <el-input v-model="formData.api_key" type="password" placeholder="请输入 API 密钥" show-password clearable />
            </div>
            <div class="lc-fld">
              <label>基础 URL <span class="lc-req">*</span></label>
              <el-input v-model="formData.base_url" placeholder="https://api.openai.com/v1" clearable />
            </div>
            <div class="lc-fld lc-fld-row">
              <div class="lc-fld-half">
                <label>协议类型</label>
                <el-select v-model="formData.api_protocol" class="w-full">
                  <el-option label="OpenAI" value="OpenAI" />
                  <el-option label="Anthropic" value="Anthropic" />
                </el-select>
              </div>
              <div class="lc-fld-half">
                <label>所属级别</label>
                <el-select v-model="formData.workspace_id" class="w-full">
                  <el-option label="系统级别" value="__system__" />
                  <el-option v-for="ws in workspaces" :key="ws.workspace_id" :label="ws.workspace_name" :value="String(ws.workspace_id)" />
                </el-select>
              </div>
            </div>
          </div>
        </div>
        <div class="lc-dlg-section lc-dlg-section-amber">
          <div class="lc-dlg-s-hd"><el-icon :size="13"><Setting /></el-icon> 状态</div>
          <div class="lc-dlg-s-bd">
            <div class="lc-switch-row">
              <span class="lc-switch-label">启用凭证</span>
              <el-switch v-model="formData.is_active" active-color="#5b6ef7" />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="lc-dlg-ft">
          <button class="lc-btn lc-btn-cancel" @click="dialogVisible = false">取消</button>
          <button class="lc-btn lc-btn-test" @click="handleTest" :disabled="testing">{{ testing ? '测试中…' : '测试连接' }}</button>
          <button class="lc-btn lc-btn-primary" @click="handleSave" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </template>
    </el-dialog>

    <!-- Delete Dialog -->
    <el-dialog v-model="deleteDialogVisible" width="380px" :close-on-click-modal="false" class="lc-dialog" top="20vh">
      <div class="lc-del-body">
        <div class="lc-del-icon"><el-icon :size="28"><Warning /></el-icon></div>
        <h3 class="lc-del-title">删除凭证</h3>
        <p class="lc-del-text">确定要删除 <strong>{{ deleteRow?.model }}</strong> 吗？此操作不可撤销。</p>
      </div>
      <template #footer>
        <div class="lc-dlg-ft">
          <button class="lc-btn lc-btn-cancel" @click="deleteDialogVisible = false">取消</button>
          <button class="lc-btn lc-btn-danger" @click="doDelete">删除</button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Search, Warning, Key, InfoFilled, Setting } from '@element-plus/icons-vue'
import { getMyManageWorkspaces } from '@/network/api.js'
import { createLLMCredential, getLLMCredentialList, updateLLMCredential, deleteLLMCredential, getLLMCredentialWithKey, testLLMConnection } from '@/network/api.js'

const credentials = ref([])
const workspaces = ref([])
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加凭证')
const filterLevel = ref('')
const filterWorkspaceId = ref(null)
const deleteDialogVisible = ref(false)
const deleteRow = ref(null)

const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const formData = ref({
  id: null,
  model: '',
  api_key: '',
  base_url: '',
  api_protocol: 'OpenAI',
  workspace_id: null,
  is_active: true
})

watch(filterLevel, () => {
  if (filterLevel.value !== 'workspace') filterWorkspaceId.value = null
})

const loadWorkspaces = async () => {
  try {
    const resp = await getMyManageWorkspaces({ page_num: 1, page_size: 100 })
    if (resp.code === 0) workspaces.value = resp.data.workspaces
  } catch { /* ignore */ }
}

const loadCredentials = async (page = 1, size = 20) => {
  loading.value = true
  try {
    const params = { page_num: page, page_size: size }
    if (filterLevel.value === 'system') params.workspace_id = 'system'
    else if (filterLevel.value === 'workspace' && filterWorkspaceId.value) params.workspace_id = filterWorkspaceId.value
    const resp = await getLLMCredentialList(params)
    if (resp.code === 0) {
      credentials.value = resp.data.list
      total.value = resp.data.total
    }
  } catch {
    ElMessage.error('加载凭证列表失败')
  } finally { loading.value = false }
}

const handlePageChange = (page) => { currentPage.value = page; loadCredentials(page, pageSize.value) }
const handleSizeChange = (size) => { pageSize.value = size; currentPage.value = 1; loadCredentials(1, size) }
const handleSearch = () => { currentPage.value = 1; loadCredentials(1, pageSize.value) }

const openCreateDialog = () => {
  dialogTitle.value = '添加凭证'
  formData.value = { id: null, model: '', api_key: '', base_url: '', api_protocol: 'OpenAI', workspace_id: null, is_active: true }
  dialogVisible.value = true
}

const openEditDialog = async (row) => {
  dialogTitle.value = '编辑凭证'
  try {
    const resp = await getLLMCredentialWithKey(row.id)
    if (resp.code === 0) {
      const wid = resp.data.workspace_id
      formData.value = {
        id: resp.data.id,
        model: resp.data.model,
        api_key: '',
        base_url: resp.data.base_url,
        api_protocol: resp.data.api_protocol,
        workspace_id: wid == null ? '__system__' : String(wid),
        is_active: resp.data.is_active
      }
      dialogVisible.value = true
    } else ElMessage.error('获取凭证详情失败')
  } catch { ElMessage.error('获取凭证详情失败') }
}

const confirmDelete = (row) => { deleteRow.value = row; deleteDialogVisible.value = true }

const doDelete = async () => {
  if (!deleteRow.value) return
  try {
    const resp = await deleteLLMCredential(deleteRow.value.id)
    if (resp.code === 0) {
      ElMessage.success('删除成功')
      deleteDialogVisible.value = false
      deleteRow.value = null
      loadCredentials()
    } else ElMessage.error(resp.msg || '删除失败')
  } catch { ElMessage.error('删除失败') }
}

const handleTest = async () => {
  if (!formData.value.model) { ElMessage.warning('请先填写模型名称'); return }
  if (!formData.value.api_key) { ElMessage.warning('请先填写 API 密钥'); return }
  if (!formData.value.base_url) { ElMessage.warning('请先填写基础 URL'); return }
  testing.value = true
  try {
    const resp = await testLLMConnection({
      model: formData.value.model,
      api_key: formData.value.api_key,
      base_url: formData.value.base_url,
      api_protocol: formData.value.api_protocol
    })
    if (resp.code === 0) {
      ElMessage.success('连接测试成功！')
    } else {
      ElMessage.error(resp.message || '连接失败')
    }
  } catch { ElMessage.error('连接测试异常') } finally { testing.value = false }
}

const handleSave = async () => {
  if (!formData.value.model) { ElMessage.warning('请输入模型名称'); return }
  if (!formData.value.api_key) { ElMessage.warning('请输入 API 密钥'); return }
  if (!formData.value.base_url) { ElMessage.warning('请输入基础 URL'); return }
  saving.value = true
  try {
    const wsId = formData.value.workspace_id === '__system__' ? null : formData.value.workspace_id
    const data = { ...formData.value, workspace_id: wsId }
    const resp = formData.value.id ? await updateLLMCredential(data) : await createLLMCredential(data)
    if (resp.code === 0) {
      ElMessage.success(formData.value.id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      loadCredentials()
    } else ElMessage.error(resp.msg || '保存失败')
  } catch { ElMessage.error('保存失败') } finally { saving.value = false }
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => { loadWorkspaces(); loadCredentials() })
</script>

<style scoped>
/* ─── Page Layout ─── */
.lc-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: #f5f5f7; }
.lc-sticky { flex-shrink: 0; display: flex; flex-direction: column; gap: 8px; position: sticky; top: 0; z-index: 10; padding-bottom: 8px; background: #f5f5f7; }
.lc-scroll { flex: 1; overflow: hidden; padding: 2px; display: flex; flex-direction: column; gap: 10px; }

/* ─── Header ─── */
.lc-header-card { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; }
.lc-header-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; }
.lc-header-left { display: flex; align-items: center; gap: 14px; }
.lc-title-group { display: flex; align-items: center; gap: 12px; }
.lc-icon-wrap { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.lc-title { margin: 0; font-size: 17px; font-weight: 700; color: #1d1d1f; }
.lc-subtitle { margin: 2px 0 0; font-size: 12px; color: #8e8e93; }
.lc-header-actions { display: flex; gap: 8px; }

/* ─── Buttons ─── */
.lc-btn { display: inline-flex; align-items: center; gap: 5px; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; padding: 7px 14px; transition: all 0.15s ease; }
.lc-btn-primary { background: #5b6ef7; color: #fff; }
.lc-btn-primary:hover { background: #4c5fd8; }
.lc-btn-ghost { background: transparent; color: #505050; border: 1px solid #d1d5db; }
.lc-btn-ghost:hover { background: #f0f0f0; }
.lc-btn-cancel { background: #f5f5f7; color: #505050; border: 1px solid #d1d5db; }
.lc-btn-cancel:hover { background: #eee; }
.lc-btn-danger { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.lc-btn-danger:hover { background: #fee2e2; }
.lc-btn-test { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.lc-btn-test:hover { background: #dcfce7; }
.lc-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ─── Filter ─── */
.lc-filter-card { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; }
.lc-filter-inner { display: flex; align-items: center; gap: 12px; padding: 10px 16px; flex-wrap: wrap; }
.lc-filter-group { display: flex; align-items: center; gap: 6px; }
.lc-filter-label { font-size: 12px; color: #8e8e93; white-space: nowrap; }
.lc-select-sm { width: 140px; }

.lc-filter-btn {
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

.lc-filter-btn:hover {
  background: #e8eef3;
}

/* ─── Table ─── */
.lc-table-wrap { flex: 1; min-height: 0; background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; overflow: hidden; }
.lc-id { font-family: monospace; font-size: 11px; color: #8e8e93; background: #f5f5f5; padding: 1px 5px; border-radius: 4px; }
.lc-model { font-size: 13px; font-weight: 500; color: #1d1d1f; }
.lc-masked { font-size: 12px; color: #c0c4cc; letter-spacing: 1px; }
.lc-url { font-size: 12px; color: #8e8e93; display: inline-block; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lc-user { font-size: 12px; color: #555; }
.lc-time { font-size: 12px; color: #8e8e93; }

/* Action buttons */
.lc-actions { display: flex; gap: 6px; justify-content: center; }
.lc-act { border: none; border-radius: 6px; font-size: 12px; padding: 4px 10px; cursor: pointer; transition: all 0.12s ease; font-weight: 500; }
.lc-act-edit { background: #eef2ff; color: #5b6ef7; }
.lc-act-edit:hover { background: #dde3ff; }
.lc-act-del { background: #fef2f2; color: #dc2626; }
.lc-act-del:hover { background: #fee2e2; }

/* ─── Pagination ─── */
.lc-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }

/* ─── Dialog ─── */
.lc-dialog :deep(.el-dialog__header) { padding: 0; }
.lc-dialog :deep(.el-dialog__body) { padding: 0; }
.lc-dialog :deep(.el-dialog__footer) { padding: 0; }

.lc-dlg-hd { display: flex; align-items: center; gap: 12px; padding: 22px 24px 0; }
.lc-dlg-icon { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.lc-dlg-title { font-size: 16px; font-weight: 600; color: #1d1d1f; }
.lc-dlg-desc { font-size: 12px; color: #8e8e93; margin-top: 1px; }

.lc-dlg-body { padding: 18px 24px; display: flex; flex-direction: column; gap: 12px; }
.lc-dlg-section { border: 1px solid #e5e7eb; border-radius: 10px; border-left: 2px solid #5b6ef7; overflow: hidden; }
.lc-dlg-section-amber { border-left-color: #e8962e; }
.lc-dlg-s-hd { display: flex; align-items: center; gap: 6px; padding: 10px 14px; background: #f5f7fd; border-bottom: 1px solid #e5e7eb; font-size: 13px; font-weight: 600; color: #374151; }
.lc-dlg-section-amber .lc-dlg-s-hd { background: #fef8f0; }
.lc-dlg-s-bd { padding: 14px; display: flex; flex-direction: column; gap: 14px; }

.lc-fld { display: flex; flex-direction: column; gap: 5px; }
.lc-fld label { font-size: 12px; font-weight: 500; color: #374151; }
.lc-fld-row { flex-direction: row; gap: 12px; }
.lc-fld-half { flex: 1; display: flex; flex-direction: column; gap: 5px; }
.lc-req { color: #dc2626; }
.w-full { width: 100%; }

.lc-switch-row { display: flex; align-items: center; justify-content: space-between; }
.lc-switch-label { font-size: 13px; font-weight: 500; color: #374151; }

.lc-dlg-ft { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 24px; border-top: 1px solid #f3f4f6; }

/* ─── Delete Dialog ─── */
.lc-del-body { text-align: center; padding: 24px 20px 16px; }
.lc-del-icon { width: 52px; height: 52px; border-radius: 50%; background: #fef2f2; color: #dc2626; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px; }
.lc-del-title { margin: 0 0 6px; font-size: 16px; font-weight: 600; color: #1d1d1f; }
.lc-del-text { margin: 0; font-size: 13px; color: #6b7280; line-height: 1.5; }
.lc-del-text strong { color: #1d1d1f; }
</style>
