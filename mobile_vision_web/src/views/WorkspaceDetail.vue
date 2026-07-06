<template>
  <div class="workspace-detail">
    <div class="sticky-header">
      <el-card class="header-card rounded-xl shadow-md border-0 overflow-hidden">
        <div class="page-header-content">
          <div class="header-left">
            <h1 class="page-title">工作空间概览</h1>
            <p class="page-subtitle">管理工作空间的资源和执行统计</p>
          </div>
          <div class="header-right">
            <div class="workspace-info">
              <span class="info-label">当前空间：</span>
              <span class="info-value font-medium">{{ workspaceData.name }}</span>
            </div>
            <el-tag v-for="manager in workspaceData.managers" :key="manager.username" size="small" class="manager-tag">
              <el-icon class="mr-1" :size="12"><User/></el-icon>
              管理员：{{ manager.nickname }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <div class="scroll-content">
      <!-- 周期 Tab -->
      <div class="period-tabs">
        <button v-for="p in periods" :key="p.value" @click="switchPeriod(p.value)" :class="['period-tab', currentPeriod === p.value ? 'active' : '']">
          {{ p.label }}
        </button>
      </div>

      <!-- 统计卡片行 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon blue">
            <el-icon :size="24"><List/></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ periodData.new_cases }}</div>
            <div class="stat-label">新增用例</div>
            <div class="stat-delta">
              <span class="delta-num">{{ periodData.active_cases }}</span>
              <span class="delta-label">
                活跃
                <el-tooltip content="指当前统计周期内有过执行记录的用例数量" placement="top">
                  <el-icon class="tip-icon" :size="12"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green">
            <el-icon :size="24"><Folder/></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ periodData.new_plans }}</div>
            <div class="stat-label">新增计划</div>
            <div class="stat-delta">
              <span class="delta-num">{{ periodData.active_plans }}</span>
              <span class="delta-label">
                活跃
                <el-tooltip content="指当前统计周期内有过执行记录的计划数量" placement="top">
                  <el-icon class="tip-icon" :size="12"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon purple">
            <el-icon :size="24"><VideoPlay/></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ periodData.executions }}</div>
            <div class="stat-label">执行次数</div>
            <div class="stat-delta">
              <span class="delta-num">{{ periodData.success_rate }}%</span>
              <span class="delta-label">
                成功率
                <el-tooltip content="指当前统计周期内执行成功的 Job 数量 / 总执行 Job 数量" placement="top">
                  <el-icon class="tip-icon" :size="12"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 图表行 -->
      <div class="charts-row">
        <el-card class="chart-card rounded-xl shadow-md border-0">
          <template #header>
            <h3 class="card-title">新增用例优先级分布</h3>
          </template>
          <div ref="priorityChartRef" class="chart-container"></div>
        </el-card>
        <el-card class="chart-card rounded-xl shadow-md border-0">
          <template #header>
            <h3 class="card-title">case执行状态分布</h3>
          </template>
          <div ref="statusChartRef" class="chart-container"></div>
        </el-card>
      </div>

      <!-- 成员管理表格 -->
      <el-card class="member-card shadow-md border-0">
        <template #header>
          <div class="member-header">
            <span class="member-title"><el-icon :size="16"><User/></el-icon> 成员管理 ({{ statistics.total_members }} 位)</span>
            <div class="member-actions">
              <el-input
                v-model="memberSearch"
                placeholder="搜索成员"
                size="small"
                clearable
                style="width: 200px; margin-right: 12px;"
              >
                <template #prefix>
                  <el-icon><Search/></el-icon>
                </template>
              </el-input>
              <el-button type="primary" size="small" @click="openAddMemberDialog">
                <el-icon><Plus/></el-icon> 添加成员
              </el-button>
            </div>
          </div>
        </template>
        <el-table
          :data="filteredMembers"
          v-loading="memberLoading"
          style="width: 100%"
          size="default"
        >
          <el-table-column label="成员" width="200">
            <template #default="{ row }">
              <div class="member-info-cell">
                <div class="member-avatar" :style="{ background: getAvatarColor(row.member_info?.username) }">
                  {{ (row.member_info?.username || '?').charAt(0).toUpperCase() }}
                </div>
                <div class="member-details">
                  <span class="member-nickname">{{ row.member_info?.nickname || row.member_info?.username || '-' }}</span>
                  <el-tooltip v-if="row.member_info?.nickname" :content="'用户名: ' + (row.member_info?.username || '-')" placement="top">
                    <span class="member-username">{{ row.member_info?.username || '-' }}</span>
                  </el-tooltip>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="200">
            <template #default="{ row }">
              <span class="role-badge" :class="getRoleClass(row.role?.role_name)">
                {{ row.role?.role_name || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="join_time" label="加入时间">
            <template #default="{ row }">
              {{ row.join_time ? new Date(row.join_time).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <button class="action-btn edit-btn" @click="openEditMemberDialog(row)">
                  <el-icon :size="14"><Edit/></el-icon>
                  <span>角色</span>
                </button>
                <button class="action-btn delete-btn" @click="handleRemoveMember(row)">
                  <el-icon :size="14"><Delete/></el-icon>
                  <span>移除</span>
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 添加成员弹窗 -->
      <el-dialog
        v-model="addMemberDialogVisible"
        width="560px"
        :close-on-click-modal="false"
        :show-close="false"
        class="member-add-dialog"
      >
        <template #header>
          <div class="add-dialog-header">
            <div class="add-header-icon">
              <el-icon :size="20"><User/></el-icon>
            </div>
            <div class="add-header-text">
              <span class="add-header-title">添加成员</span>
              <span class="add-header-subtitle">将新成员添加到当前工作空间</span>
            </div>
            <button class="add-header-close" @click="addMemberDialogVisible = false">
              <el-icon :size="18"><Close/></el-icon>
            </button>
          </div>
        </template>

        <div class="add-dialog-body">
          <!-- 用户搜索输入 -->
          <div class="add-field-section">
            <label class="add-field-label">
              <el-icon :size="14"><User/></el-icon>
              搜索用户
            </label>
            <div class="add-input-wrapper">
              <el-autocomplete
                v-model="newMemberForm.displayName"
                :fetch-suggestions="searchUsers"
                :trigger-on-focus="false"
                placeholder="输入用户名或昵称搜索..."
                class="add-user-autocomplete"
                size="large"
                clearable
                @select="handleSelectUser"
              >
                <template #prefix>
                  <el-icon class="add-input-icon"><Search/></el-icon>
                </template>
                <template #default="{ item }">
                  <div class="user-suggestion-item">
                    <div class="user-sug-avatar">{{ (item.nickname || item.username).charAt(0).toUpperCase() }}</div>
                    <div class="user-sug-info">
                      <span class="user-sug-nickname">{{ item.nickname }}</span>
                      <span class="user-sug-username">{{ item.username }}</span>
                    </div>
                  </div>
                </template>
              </el-autocomplete>
            </div>
          </div>

          <!-- 角色选择 -->
          <div class="add-field-section">
            <label class="add-field-label">
              <el-icon :size="14"><CircleCheck/></el-icon>
              选择角色
            </label>
            <div class="add-role-grid">
              <div
                v-for="role in roles"
                :key="role.id"
                class="add-role-card"
                :class="{ 'selected': newMemberForm.role_id === role.id }"
                @click="newMemberForm.role_id = role.role_id"
              >
                <div class="add-role-icon" :class="'role-icon-' + (role.role_name === '管理员' ? 'admin' : role.role_name === '开发' ? 'dev' : role.role_name === '测试' ? 'qa' : role.role_name === '产品' ? 'pm' : 'default')">
                  {{ role.role_name === '管理员' ? '👑' : role.role_name === '开发' ? '💻' : role.role_name === '测试' ? '🔍' : role.role_name === '产品' ? '📋' : '📌' }}
                </div>
                <div class="add-role-body">
                  <div class="add-role-name-row">
                    <span class="add-role-name">{{ role.role_name }}</span>
                    <el-icon v-if="newMemberForm.role_id === role.role_id" class="add-role-check">
                      <CircleCheckFilled/>
                    </el-icon>
                  </div>
                  <span class="add-role-desc">{{ role.role_description || '暂无描述' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="add-dialog-footer">
            <button class="add-btn-cancel" @click="addMemberDialogVisible = false">取消</button>
            <button class="add-btn-confirm" @click="handleAddMember">
              <el-icon :size="16"><Plus/></el-icon>
              添加成员
            </button>
          </div>
        </template>
      </el-dialog>

      <!-- 修改角色弹窗 -->
      <el-dialog
        v-model="editMemberDialogVisible"
        width="560px"
        :close-on-click-modal="false"
        :show-close="false"
        class="member-add-dialog"
      >
        <template #header>
          <div class="add-dialog-header">
            <div class="add-header-icon edit">
              <el-icon :size="20"><Edit/></el-icon>
            </div>
            <div class="add-header-text">
              <span class="add-header-title">修改成员角色</span>
              <span class="add-header-subtitle">调整成员在工作空间中的权限</span>
            </div>
            <button class="add-header-close" @click="editMemberDialogVisible = false">
              <el-icon :size="18"><Close/></el-icon>
            </button>
          </div>
        </template>

        <div class="add-dialog-body">
          <!-- 角色选择 -->
          <div class="add-field-section">
            <label class="add-field-label">
              <el-icon :size="14"><CircleCheck/></el-icon>
              选择新角色
            </label>
            <div class="add-role-grid">
              <div
                v-for="role in roles"
                :key="role.id"
                class="add-role-card"
                :class="{ 'selected': editMemberForm.role_id === role.id }"
                @click="editMemberForm.role_id = role.role_id"
              >
                <div class="add-role-icon" :class="'role-icon-' + (role.role_name === '管理员' ? 'admin' : role.role_name === '开发' ? 'dev' : role.role_name === '测试' ? 'qa' : role.role_name === '产品' ? 'pm' : 'default')">
                  {{ role.role_name === '管理员' ? '👑' : role.role_name === '开发' ? '💻' : role.role_name === '测试' ? '🔍' : role.role_name === '产品' ? '📋' : '📌' }}
                </div>
                <div class="add-role-body">
                  <div class="add-role-name-row">
                    <span class="add-role-name">{{ role.role_name }}</span>
                    <el-icon v-if="editMemberForm.role_id === role.role_id" class="add-role-check">
                      <CircleCheckFilled/>
                    </el-icon>
                  </div>
                  <span class="add-role-desc">{{ role.role_description || '暂无描述' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="add-dialog-footer">
            <button class="add-btn-cancel" @click="editMemberDialogVisible = false">取消</button>
            <button class="add-btn-confirm edit" @click="handleEditMember">
              <el-icon :size="16"><Edit/></el-icon>
              确认修改
            </button>
          </div>
        </template>
      </el-dialog>

      <!-- 移除成员确认弹窗 -->
      <el-dialog
        v-model="deleteDialogVisible"
        title="确认移除"
        width="400px"
        :close-on-click-modal="false"
      >
        <div class="text-center py-4">
          <el-icon :size="48" class="text-red-500 mb-4"><Warning/></el-icon>
          <p class="text-gray-700">确定要移除成员 <strong>{{ deleteMemberData?.member_info?.nickname || deleteMemberData?.member_info?.username }}</strong> 吗？</p>
          <p class="text-gray-500 text-sm mt-2">此操作不可撤销，请谨慎操作</p>
        </div>
        <template #footer>
          <div class="flex justify-end gap-3">
            <el-button @click="deleteDialogVisible = false">取消</el-button>
            <el-button type="danger" @click="confirmRemoveMember">确定移除</el-button>
          </div>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { User, List, Folder, VideoPlay, QuestionFilled, Plus, Edit, Delete, Search, CircleCheckFilled, Warning, Close, CircleCheck } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { getWorkspaceDetail, getWorkspaceMembers, addMemberByAdmin, updateMemberRole, removeMemberFromWorkspace, getRolesList, getUserList } from '@/network/api.js';

const workspaceData = ref({ id: '', name: '', managers: [] });

const statistics = ref({
  total_cases: 0,
  total_plans: 0,
  active_plans: 0,
  total_executions: 0,
  total_members: 0,
  case_by_level: {},
  execution_by_status: {},
  period_data: { new_cases: 0, active_cases: 0, new_plans: 0, active_plans: 0, executions: 0, success_rate: 0 },
  period_charts: { case_by_level: {}, execution_by_status: {} }
});

const currentPeriod = ref('total');
const periods = [
  { label: '全部', value: 'total' },
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' }
];

const periodData = computed(() => {
  return statistics.value.period_data || { new_cases: 0, active_cases: 0, new_plans: 0, active_plans: 0, executions: 0, success_rate: 0 };
});

const priorityChartRef = ref(null);
const statusChartRef = ref(null);
let priorityChart = null;
let statusChart = null;

// 成员管理相关状态
const members = ref([]);
const roles = ref([]);
const memberLoading = ref(false);
const memberSearch = ref('');
const addMemberDialogVisible = ref(false);
const editMemberDialogVisible = ref(false);
const deleteDialogVisible = ref(false);
const deleteMemberData = ref(null);
const newMemberForm = ref({ username: '', displayName: '', role_id: '' });
const editMemberForm = ref({ member_id: '', role_id: '' });
const currentWorkspaceId = ref('');

const loadStatistics = async () => {
  const workspaceId = window.location.pathname.split('/')[2];
  try {
    const res = await getWorkspaceDetail({ workspace_id: workspaceId, period: currentPeriod.value });
    if (res.code === 0) {
      workspaceData.value = {
        id: res.data.workspace_id,
        name: res.data.workspace_name,
        managers: res.data.manager || []
      };

      const statData = res.data.statistics || {};
      statistics.value = {
        total_cases: statData.total_cases || 0,
        total_plans: statData.total_plans || 0,
        active_plans: statData.active_plans || 0,
        total_executions: statData.total_executions || 0,
        total_members: statData.total_members || 0,
        case_by_level: statData.case_by_level || {},
        execution_by_status: statData.execution_by_status || {},
        period_data: statData.period_data || { new_cases: 0, active_cases: 0, new_plans: 0, active_plans: 0, executions: 0, success_rate: 0 },
        period_charts: statData.period_charts || { case_by_level: {}, execution_by_status: {} },
      };

      await nextTick();
      updateCharts();
    } else {
      ElMessage.error(res.message || '获取统计数据失败');
    }
  } catch (error) {
    console.error('获取统计数据失败:', error);
    ElMessage.error('获取统计数据失败');
  }
};

const switchPeriod = (period) => {
  currentPeriod.value = period;
  loadStatistics();
};

// 成员管理相关方法
const loadMembers = async () => {
  if (!currentWorkspaceId.value) return;
  memberLoading.value = true;
  try {
    const res = await getWorkspaceMembers({
      workspace_id: currentWorkspaceId.value,
      page_num: 1,
      page_size: 100
    });
    if (res.code === 0) {
      members.value = res.data || [];
    }
  } catch (error) {
    console.error('获取成员列表失败:', error);
  } finally {
    memberLoading.value = false;
  }
};

const loadRoles = async () => {
  try {
    const res = await getRolesList();
    if (res.code === 0) {
      roles.value = res.data || [];
    }
  } catch (error) {
    console.error('获取角色列表失败:', error);
  }
};

// 用户搜索（用于添加成员弹窗的自动补全）
const searchUsers = async (query, cb) => {
  if (!query || query.trim().length < 1) {
    cb([]);
    return;
  }
  try {
    const res = await getUserList({ search: query.trim(), page_num: 1, page_size: 20 });
    if (res.code === 0) {
      const users = (res.data?.list || []).filter(u => !u.is_deleted);
      cb(users);
    } else {
      cb([]);
    }
  } catch {
    cb([]);
  }
};

const handleSelectUser = (item) => {
  newMemberForm.value.username = item.username;
  newMemberForm.value.displayName = `${item.nickname || item.username}(${item.username})`;
};

const openAddMemberDialog = () => {
  newMemberForm.value = { username: '', displayName: '', role_id: '' };
  addMemberDialogVisible.value = true;
};

const handleAddMember = async () => {
  if (!newMemberForm.value.username || !newMemberForm.value.role_id) {
    ElMessage.warning('请填写完整信息');
    return;
  }
  try {
    const res = await addMemberByAdmin({
      workspace_id: currentWorkspaceId.value,
      username: newMemberForm.value.username,
      role_id: newMemberForm.value.role_id
    });
    if (res.code === 0) {
      ElMessage.success('添加成员成功');
      addMemberDialogVisible.value = false;
      loadMembers();
    } else {
      ElMessage.warning(res.message || '添加成员失败，请检查用户是否存在');
    }
  } catch (error) {
    console.error('添加成员失败:', error);
    ElMessage.error(error?.response?.data?.message || '添加成员失败，请检查用户是否存在');
  }
};

const openEditMemberDialog = (member) => {
  editMemberForm.value = {
    member_id: member.member_id,
    role_id: member.role?.role_id || ''
  };
  editMemberDialogVisible.value = true;
};

const handleEditMember = async () => {
  if (!editMemberForm.value.role_id) {
    ElMessage.warning('请选择角色');
    return;
  }
  try {
    const res = await updateMemberRole({
      member_id: editMemberForm.value.member_id,
      role_id: editMemberForm.value.role_id
    });
    if (res.code === 0) {
      ElMessage.success('修改角色成功');
      editMemberDialogVisible.value = false;
      loadMembers();
    } else {
      ElMessage.error(res.message || '修改角色失败');
    }
  } catch (error) {
    console.error('修改角色失败:', error);
    ElMessage.error('修改角色失败');
  }
};

const handleRemoveMember = (member) => {
  deleteMemberData.value = member;
  deleteDialogVisible.value = true;
};

const confirmRemoveMember = async () => {
  if (!deleteMemberData.value) return;
  try {
    const res = await removeMemberFromWorkspace(deleteMemberData.value.member_id);
    if (res.code === 0) {
      ElMessage.success('移除成员成功');
      deleteDialogVisible.value = false;
      deleteMemberData.value = null;
      loadMembers();
    } else {
      ElMessage.error(res.message || '移除成员失败');
    }
  } catch (error) {
    console.error('移除成员失败:', error);
    ElMessage.error('移除成员失败');
  }
};

const filteredMembers = computed(() => {
  if (!memberSearch.value) return members.value;
  const search = memberSearch.value.toLowerCase();
  return members.value.filter(m =>
    m.member_info?.username?.toLowerCase().includes(search)
  );
});

// 根据用户名生成头像颜色
const avatarColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
  'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
  'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
];

const getAvatarColor = (username) => {
  if (!username) return avatarColors[0];
  const hash = username.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return avatarColors[hash % avatarColors.length];
};

// 角色名称到 CSS class 的映射
const roleClassMap = {
  '管理员': 'role-admin',
  '开发': 'role-dev',
  '测试': 'role-qa',
  '产品': 'role-pm',
};

const getRoleClass = (roleName) => {
  return roleClassMap[roleName] || 'role-default';
};

const initCharts = () => {
  if (priorityChartRef.value && !priorityChart) {
    priorityChart = echarts.init(priorityChartRef.value);
  }
  if (statusChartRef.value && !statusChart) {
    statusChart = echarts.init(statusChartRef.value);
  }
};

const updateCharts = () => {
  initCharts();

  if (priorityChart) {
    const levelData = statistics.value.period_charts.case_by_level || {};
    priorityChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['P0', 'P1', 'P2', 'P3'], axisLabel: { fontSize: 12 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 12 } },
      series: [{
        name: '用例数',
        type: 'bar',
        barWidth: '50%',
        data: [
          { value: levelData.P0 || 0, itemStyle: { color: '#ef4444' } },
          { value: levelData.P1 || 0, itemStyle: { color: '#f59e0b' } },
          { value: levelData.P2 || 0, itemStyle: { color: '#3b82f6' } },
          { value: levelData.P3 || 0, itemStyle: { color: '#22c55e' } }
        ],
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }]
    });
  }

  if (statusChart) {
    const execData = statistics.value.period_charts.execution_by_status || {};
    statusChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, left: 'center' },
      series: [{
        name: '执行状态',
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: execData.pending || 0, name: '待执行', itemStyle: { color: '#3b82f6' } },
          { value: execData.running || 0, name: '执行中', itemStyle: { color: '#f59e0b' } },
          { value: execData.completed || 0, name: '已完成', itemStyle: { color: '#22c55e' } },
          { value: execData.failed || 0, name: '失败', itemStyle: { color: '#ef4444' } },
          { value: execData.aborted || 0, name: '已放弃', itemStyle: { color: '#6b7280' } }
        ].filter(item => item.value > 0)
      }]
    });
  }
};

onMounted(() => {
  currentWorkspaceId.value = window.location.pathname.split('/')[2];
  loadStatistics();
  loadRoles();
  loadMembers();
});
</script>

<style scoped>
.workspace-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f5f5f5;
  padding-bottom: 10px;
}

.scroll-content {
  flex: 1;
  overflow-y: auto;
  padding-top: 10px;
}

.header-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

.page-header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  padding: 1rem;
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
  color: #1f2937;
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  color: #6b7280;
  margin: 4px 0 0;
}

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.workspace-info {
  font-size: 12px;
  color: #6b7280;
}

.info-label {
  color: #9ca3af;
}

.info-value {
  color: #1f2937;
}

.manager-tag {
  background: #dbeafe;
  color: #2563eb;
  border: none;
}

.period-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  background: #ffffff;
  border-radius: 10px;
  padding: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.period-tab {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.25s;
}

.period-tab:hover {
  color: #3b82f6;
  background: #f0f5ff;
}

.period-tab.active {
  background: #3b82f6;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.blue {
  background: #dbeafe;
  color: #2563eb;
}

.stat-icon.green {
  background: #dcfce7;
  color: #16a34a;
}

.stat-icon.purple {
  background: #ede9fe;
  color: #7c3aed;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #1f2937;
  line-height: 1.1;
  margin-bottom: 2px;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 8px;
}

.stat-delta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.delta-num {
  font-weight: 600;
  color: #22c55e;
}

.delta-label {
  color: #9ca3af;
  display: flex;
  align-items: center;
  gap: 3px;
}

.tip-icon {
  color: #c4c9d2;
  cursor: help;
  transition: color 0.2s;
}

.tip-icon:hover {
  color: #9ca3af;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
  .stats-row {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  min-height: 260px;
}

.chart-container {
  width: 100%;
  height: 200px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

:deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: none;
}

:deep(.el-card__body) {
  padding: 16px;
}

.member-card {
  border-radius: 16px;
  overflow: hidden;
}

.member-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.member-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.member-actions {
  display: flex;
  align-items: center;
}

/* 成员单元格样式 */
.member-info-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.member-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.member-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.member-nickname {
  font-weight: 500;
  color: #1f2937;
  font-size: 14px;
}

.member-username {
  font-size: 11px;
  color: #9ca3af;
  cursor: help;
}

/* 角色标签样式 */
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.3px;
  transition: all 0.2s ease;
}

.role-badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.role-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.role-admin {
  background: linear-gradient(135deg, #fef3f2 0%, #fee4e2 100%);
  color: #d92d20;
  border: 1px solid #fecdca;
}

.role-admin::before {
  background: #f04438;
  box-shadow: 0 0 4px rgba(240, 68, 56, 0.4);
}

.role-dev {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.role-dev::before {
  background: #3b82f6;
  box-shadow: 0 0 4px rgba(59, 130, 246, 0.4);
}

.role-qa {
  background: linear-gradient(135deg, #fdf4ff 0%, #fae8ff 100%);
  color: #9333ea;
  border: 1px solid #e9d5ff;
}

.role-qa::before {
  background: #a855f7;
  box-shadow: 0 0 4px rgba(168, 85, 247, 0.4);
}

.role-pm {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  color: #059669;
  border: 1px solid #a7f3d0;
}

.role-pm::before {
  background: #10b981;
  box-shadow: 0 0 4px rgba(16, 185, 129, 0.4);
}

.role-default {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.role-default::before {
  background: #9ca3af;
}

/* ===== 添加/编辑成员弹窗 - 全新设计 ===== */
.member-add-dialog :deep(.el-dialog) {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.15), 0 8px 24px rgba(0, 0, 0, 0.08);
  background: #ffffff;
}

.member-add-dialog :deep(.el-dialog__header) {
  padding: 0;
  margin: 0;
  border-bottom: 1px solid #f3f4f6;
}

.member-add-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.member-add-dialog :deep(.el-dialog__footer) {
  padding: 0;
}

/* 弹窗头部 */
.add-dialog-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #fafbfc 0%, #ffffff 100%);
}

.add-header-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #2563eb;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.15);
}

.add-header-icon.edit {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  box-shadow: 0 4px 10px rgba(245, 158, 11, 0.15);
}

.add-header-text {
  flex: 1;
  min-width: 0;
}

.add-header-title {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  line-height: 1.3;
}

.add-header-subtitle {
  display: block;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
}

.add-header-close {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.add-header-close:hover {
  background: #fef2f2;
  color: #ef4444;
  transform: rotate(90deg);
}

/* 弹窗内容 */
.add-dialog-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.add-field-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.add-field-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  padding-left: 2px;
}

/* 用户搜索自动补全 */
.add-input-wrapper {
  position: relative;
}

.add-user-autocomplete {
  width: 100%;
}

.add-user-autocomplete :deep(.el-input__wrapper) {
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: none;
  padding: 4px 16px;
  transition: all 0.25s ease;
  height: 48px;
}

.add-user-autocomplete :deep(.el-input__wrapper:hover) {
  border-color: #93c5fd;
  background: #f8fafc;
}

.add-user-autocomplete :deep(.el-input__wrapper.is-focus) {
  border-color: #3b82f6;
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.add-user-autocomplete :deep(.el-input__inner) {
  font-size: 14px;
  color: #111827;
  height: 40px;
}

.add-user-autocomplete :deep(.el-input__inner::placeholder) {
  color: #9ca3af;
  font-size: 13px;
}

.add-input-icon {
  color: #9ca3af;
  font-size: 16px;
}

/* 自动补全下拉选项样式 */
.add-user-autocomplete :deep(.el-autocomplete-suggestion) {
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
  padding: 8px;
  margin-top: 4px;
  border: none;
  overflow: hidden;
}

.add-user-autocomplete :deep(.el-autocomplete-suggestion__list) {
  max-height: 300px;
}

.add-user-autocomplete :deep(.el-autocomplete-suggestion li) {
  padding: 8px 10px;
  border-radius: 10px;
  transition: all 0.15s ease;
  margin: 2px 0;
}

.add-user-autocomplete :deep(.el-autocomplete-suggestion li:hover) {
  background: #f0f9ff;
}

.add-user-autocomplete :deep(.el-autocomplete-suggestion li.highlighted) {
  background: #eff6ff;
}

/* 下拉选项内容 */
.user-suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 2px 0;
}

.user-sug-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
}

.user-sug-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.user-sug-nickname {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.user-sug-username {
  font-size: 11px;
  color: #9ca3af;
}

/* 角色选择网格 */
.add-role-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.add-role-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 16px;
  border: 2px solid #e5e7eb;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.add-role-card:hover {
  border-color: #93c5fd;
  background: #f8fafc;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.1);
}

.add-role-card.selected {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.15);
}

.add-role-card.selected::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 16px;
  border: 2px solid transparent;
  pointer-events: none;
}

/* 角色图标 */
.add-role-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.role-icon-admin {
  background: linear-gradient(135deg, #fef3f2 0%, #fee4e2 100%);
  box-shadow: 0 2px 8px rgba(240, 68, 56, 0.1);
}

.role-icon-dev {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.role-icon-qa {
  background: linear-gradient(135deg, #fdf4ff 0%, #fae8ff 100%);
  box-shadow: 0 2px 8px rgba(168, 85, 247, 0.1);
}

.role-icon-pm {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
}

.role-icon-default {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  box-shadow: 0 2px 8px rgba(107, 114, 128, 0.1);
}

/* 角色文本 */
.add-role-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.add-role-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.add-role-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.add-role-check {
  color: #3b82f6;
  font-size: 18px;
  animation: checkPop 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes checkPop {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}

.add-role-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 弹窗底部 */
.add-dialog-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
  background: #fafbfc;
}

.add-btn-cancel {
  padding: 10px 24px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-btn-cancel:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  color: #374151;
}

.add-btn-confirm {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.add-btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.35);
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

.add-btn-confirm:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
}

.add-btn-confirm.edit {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.25);
}

.add-btn-confirm.edit:hover {
  box-shadow: 0 8px 20px rgba(245, 158, 11, 0.35);
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
}

/* 表格样式优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th) {
  background: #f9fafb;
  color: #4b5563;
  font-weight: 500;
  font-size: 13px;
}

:deep(.el-table tr:hover > td) {
  background: #f9fafb;
}

:deep(.el-table td) {
  padding: 12px 0;
}

/* 表格操作按钮容器 */
.table-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  background: transparent;
}

/* 编辑角色按钮 - 柔和的蓝色调 */
.edit-btn {
  color: #3b82f6;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.edit-btn:hover {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.15);
}

/* 移除按钮 - 柔和的红色调 */
.delete-btn {
  color: #ef4444;
  background: #fef2f2;
  border-color: #fecaca;
}

.delete-btn:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.15);
}

/* 添加成员按钮样式 */
:deep(.el-button--small.el-button--primary) {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: 500;
}

:deep(.el-button--small.el-button--primary:hover) {
  background: linear-gradient(135deg, #4b5563 0%, #374151 100%);
  box-shadow: 0 4px 12px rgba(107, 114, 128, 0.25);
}
</style>
