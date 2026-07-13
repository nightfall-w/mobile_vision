<template>
  <div class="system-config-container">
    <!-- 头部导航 -->
    <Header/>

    <div v-if="hasPermission" class="main-content">
      <div class="config-header">
        <!-- 左侧：标题和描述 -->
        <div class="header-left">
          <h1>系统配置管理</h1>
          <p>管理系统级别的配置项</p>
        </div>

        <!-- 右侧：管理员信息和按钮 -->
        <div class="header-right">
          <div class="admins-display">
            <span class="admins-label">管理员:</span>
            <div class="admins-list">
              <el-tag
                v-for="admin in allAdmins"
                :key="admin.id"
                class="admin-tag"
                :type="admin.isEnvAdmin ? 'danger' : 'success'"
                :closable="!admin.isEnvAdmin && allAdmins.length > 1"
                @close="removeAdmin(admin)"
              >
                {{ admin.nickname || admin.username }}
                <el-tooltip
                  v-if="admin.isEnvAdmin"
                  content="环境变量管理员，无法移除"
                  placement="top"
                >
                  <el-icon class="lock-icon">
                    <Lock/>
                  </el-icon>
                </el-tooltip>
              </el-tag>
            </div>
          </div>
          <el-button
            type="primary"
            @click="openAdminDialog"
            class="add-admin-btn"
            size="small"
          >
            增加/修改管理员
          </el-button>
        </div>
      </div>


      <!-- 配置项表格 -->
      <div class="table-container">
        <el-table
          :data="configList"
          v-loading="loading"
          style="width: 100%"
          class="config-table"
          stripe
          :cell-style="{ textAlign: 'center' }"
          :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
        >
          <el-table-column prop="key" label="键名" min-width="150">
            <template #default="scope">
              <span class="key-text">{{ scope.row.key }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="值" min-width="180">
            <template #default="scope">
              <div class="value-cell">
                <span class="value-text">{{ scope.row.value }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="desc" label="描述" min-width="200">
            <template #default="scope">
              <div class="desc-cell">
                <span class="desc-text">{{ scope.row.desc }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100" align="center">
            <template #default="scope">
              <el-tag :type="getTypeTagType(scope.row.type)" class="type-tag">
                {{ getConfigTypeLabel(scope.row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="required" label="必填" width="80" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.required ? 'success' : 'info'" class="status-tag">
                {{ scope.row.required ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="verified" label="通过验证" width="100" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.verified ? 'success' : 'danger'" class="status-tag">
                {{ scope.row.verified ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="update_time" label="更新时间" width="160" align="center">
            <template #default="scope">
              <span class="time-text">{{ formatTime(scope.row.update_time) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right" align="center">
            <template #default="scope">
              <div class="action-cell">
                <el-button
                  size="small"
                  type="primary"
                  link
                  @click="openEditDialog(scope.row)"
                  class="action-button"
                >
                  编辑
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div v-else class="no-permission-container">
      <div class="no-permission-content">
        <el-icon class="no-permission-icon">
          <Lock/>
        </el-icon>
        <h2>访问被拒绝</h2>
        <p>您没有权限访问此页面。只有超级管理员才能访问系统配置管理页面。</p>
        <el-button type="primary" @click="goToHome">返回首页</el-button>
      </div>
    </div>

    <!-- 固定在底部的分页 -->
    <div v-if="hasPermission" class="sc-page-footer">
      <el-pagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        background
        small
      />
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-if="hasPermission"
      :title="dialogTitle"
      v-model="dialogVisible"
      width="600px"
      :before-close="handleDialogClose"
      class="config-dialog"
    >
      <el-form
        ref="configFormRef"
        :model="configForm"
        :rules="configFormRules"
        label-width="80px"
        class="config-form"
        size="small"
      >
        <el-form-item label="键名" prop="key">
          <el-input
            v-model="configForm.key"
            placeholder="请输入配置项键名"
            disabled
            class="form-input"
          />
        </el-form-item>

        <el-form-item label="类型" prop="type">
          <el-select
            v-model="configForm.type"
            placeholder="请选择配置项类型"
            style="width: 100%"
            disabled
            class="form-select"
          >
            <el-option label="字符串" value="STRING"/>
            <el-option label="数字" value="NUMBER"/>
            <el-option label="布尔值" value="BOOLEAN"/>
            <el-option label="字典" value="DICT"/>
            <el-option label="列表" value="LIST"/>
          </el-select>
        </el-form-item>

        <el-form-item
          label="值"
          prop="value"
          :required="configForm.required"
        >
          <el-input
            v-model="configForm.value"
            type="textarea"
            placeholder="请输入配置项值"
            :rows="3"
            @input="handleValueInput"
            class="form-textarea"
          />
          <div class="value-preview-container">
            <div class="value-preview"
                 v-if="valuePreview && (configForm.required || configForm.value)">
              <div class="preview-label">值预览:</div>
              <div class="preview-content">
                <pre>{{ valuePreview }}</pre>
              </div>
              <div class="preview-type"
                   :class="{ 'success': isValueTypeValid, 'error': !isValueTypeValid }">
                类型检查: {{ valueTypeCheckMessage }}
              </div>
            </div>
            <div class="value-preview" v-else-if="!configForm.required && !configForm.value">
              <div class="preview-type">
                非必填项，值可以为空
              </div>
            </div>
            <div class="value-preview" v-else-if="configForm.required && !configForm.value">
              <div class="preview-type error">
                必填项，值不能为空
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="描述" prop="desc">
          <el-input
            v-model="configForm.desc"
            type="textarea"
            placeholder="请输入配置项描述"
            :rows="4"
            class="form-textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false"
                     class="footer-button cancel-button"
                     size="small">取消</el-button>
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="submitLoading"
            :disabled="configForm.required && !configForm.value"
            class="footer-button confirm-button"
            size="small"
          >
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 管理员管理对话框 -->
    <el-dialog
      v-if="hasPermission"
      title="管理员管理"
      v-model="adminDialogVisible"
      width="800px"
      class="admin-dialog"
    >
      <div class="admin-management">
        <div class="admin-section">
          <h3>添加管理员</h3>
          <div class="add-admin-form">
            <el-form
              ref="adminFormRef"
              :model="adminForm"
              :rules="adminFormRules"
              label-width="80px"
              size="small"
            >
              <el-form-item label="选择用户" prop="userIds">
                <el-select
                  v-model="adminForm.userIds"
                  filterable
                  remote
                  reserve-keyword
                  placeholder="请输入用户名搜索"
                  :remote-method="searchUsers"
                  :loading="userSearchLoading"
                  multiple
                  style="width: 100%"
                >
                  <el-option
                    v-for="user in [...searchedUsers, ...extraAdmins]"
                    :key="user.id"
                    :label="`${user.username} (${user.nickname})`"
                    :value="user.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  @click="saveAdmins"
                  :loading="adminSubmitLoading"
                  :disabled="!adminForm.userIds?.length"
                  size="small"
                >
                  保存管理员
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="admin-section">
          <h3>当前管理员列表</h3>
          <el-table
            :data="extraAdmins"
            style="width: 100%"
            v-loading="adminListLoading"
            size="small"
          >
            <el-table-column prop="username" label="用户名" width="150"/>
            <el-table-column prop="nickname" label="昵称" width="150"/>
            <el-table-column prop="email" label="邮箱"/>
            <el-table-column prop="created_at" label="添加时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="scope">
                <el-button
                  size="small"
                  type="danger"
                  link
                  @click="removeAdmin(scope.row)"
                  :disabled="extraAdmins.length <= 1"
                >
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="admin-note">
            <p>注意：环境变量中配置的超级管理员无法在此处移除</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>


<script setup>
import {ref, reactive, onMounted, computed} from 'vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {Lock} from '@element-plus/icons-vue'
import {useRouter} from 'vue-router'
import Header from '@/components/Header.vue'
import {
  getExtraAdminList,
  getSystemConfigList,
  updateSuperAdmin,
  updateSystemConfig
} from '@/network/api.js'
import {getUserList} from '@/network/api.js'

const router = useRouter()

// 权限控制
const hasPermission = ref(true)

// 数据状态
const configList = ref([])
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)

// 管理员相关
const adminDialogVisible = ref(false)
const adminListLoading = ref(false)
const userSearchLoading = ref(false)
const adminSubmitLoading = ref(false)
const allAdmins = ref([]) // 包含环境变量管理员和额外添加的管理员
const extraAdmins = ref([]) // 仅额外添加的管理员
const searchedUsers = ref([])

// 值预览相关
const valuePreview = ref('')
const isValueTypeValid = ref(true)
const valueTypeCheckMessage = ref('')

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 表单
const configFormRef = ref()
const configForm = reactive({
  id: '',
  key: '',
  value: '',
  desc: '',
  type: 'STRING',
  required: false
})

// 管理员表单
const adminFormRef = ref()
const adminForm = reactive({
  userIds: [] // ID数组
})

// 表单验证规则
const configFormRules = {
  key: [
    {required: true, message: '请输入键名', trigger: 'blur'}
  ],
  value: computed(() => {
    return configForm.required
      ? [{required: true, message: '请输入值', trigger: 'blur'}]
      : [{required: false}]
  }),
  desc: [
    {required: true, message: '请输入描述', trigger: 'blur'}
  ],
  type: [
    {required: true, message: '请选择类型', trigger: 'change'}
  ]
}

// 管理员表单验证规则
const adminFormRules = {
  userIds: [
    {required: true, message: '请选择用户', trigger: 'change'}
  ]
}

// 对话框标题
const dialogTitle = computed(() => {
  return '编辑配置项'
})

// 组件挂载时获取数据
onMounted(() => {
  fetchConfigList()
  fetchAdminList()
})

// 获取配置列表
const fetchConfigList = async () => {
  loading.value = true
  try {
    const res = await getSystemConfigList({
      page_num: pagination.currentPage,
      page_size: pagination.pageSize
    })

    if (res.code === 0) {
      configList.value = res.data.configs || []
      pagination.total = res.data.total || 0
    } else {
      ElMessage.error(res.message || '获取配置列表失败')
    }
  } catch (error) {
    if (error.message === '无权限访问') {
      hasPermission.value = false
    } else {
      ElMessage.error('获取配置列表失败: ' + error.message)
    }
  } finally {
    loading.value = false
  }
}

// 获取管理员列表
const fetchAdminList = async () => {
  try {
    // 获取环境变量中的管理员
    const envAdmin = {
      id: 0,
      username: 'admin',
      nickname: '超级管理员',
      email: 'admin@example.com',
      isEnvAdmin: true
    }

    // 获取额外管理员列表（从后端）
    const res = await getExtraAdminList()
    if (res.code === 0) {
      extraAdmins.value = res.data || []
    } else {
      ElMessage.error('获取管理员列表失败')
      extraAdmins.value = []
    }

    allAdmins.value = [envAdmin, ...extraAdmins.value]
  } catch (error) {
    ElMessage.error('获取管理员列表失败: ' + error.message)
  }
}

// 搜索用户
const searchUsers = async (query) => {
  if (!query) {
    searchedUsers.value = []
    return
  }

  userSearchLoading.value = true
  try {
    const res = await getUserList({
      page_num: 1,
      page_size: 20,
      search: query
    })

    if (res.code === 0) {
      const adminIds = extraAdmins.value.map(admin => admin.id)
      searchedUsers.value = (res.data.list || []).filter(user =>
        !adminIds.includes(user.id) && user.id !== 0
      )
    } else {
      ElMessage.error(res.message || '搜索用户失败')
    }
  } catch (error) {
    ElMessage.error('搜索用户失败: ' + error.message)
  } finally {
    userSearchLoading.value = false
  }
}

// 打开管理员对话框
const openAdminDialog = () => {
  adminDialogVisible.value = true
  searchedUsers.value = []
  // 初始化已选择的管理员
  adminForm.userIds = extraAdmins.value.map(admin => admin.id)
}

// 保存管理员
const saveAdmins = async () => {
  if (adminFormRef.value) {
    try {
      await adminFormRef.value.validate()
    } catch (error) {
      ElMessage.warning('请选择用户')
      return
    }
  }

  if (!adminForm.userIds || adminForm.userIds.length === 0) {
    ElMessage.warning('请选择用户')
    return
  }

  if (adminForm.userIds.length > 3) {
    ElMessage.warning('最多只能添加3个额外管理员')
    return
  }

  adminSubmitLoading.value = true
  try {
    await updateSuperAdmin({user_ids: adminForm.userIds})

    ElMessage.success('管理员列表更新成功')
    adminDialogVisible.value = false
    fetchAdminList()
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
  } finally {
    adminSubmitLoading.value = false
  }
}

// 移除管理员
const removeAdmin = async (admin) => {
  if (admin.isEnvAdmin) {
    ElMessage.warning('无法移除环境变量中的管理员')
    return
  }

  if (extraAdmins.value.length <= 1) {
    ElMessage.warning('至少需要保留一个额外管理员')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要移除管理员 ${admin.nickname || admin.username} 吗？`,
      '确认移除',
      {
        type: 'warning'
      }
    )

    // 从本地列表中移除该管理员
    const updatedAdminIds = extraAdmins.value
      .filter(a => a.id !== admin.id)
      .map(a => a.id)

    // 直接调用后端接口更新管理员列表
    await updateSuperAdmin({user_ids: updatedAdminIds})

    ElMessage.success('移除管理员成功')
    fetchAdminList() // 刷新列表
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('移除失败: ' + error.message)
    }
  }
}

// 格式化时间
const formatTime = (timeString) => {
  if (!timeString) return '-'
  return new Date(timeString).toLocaleString('zh-CN')
}

// 获取配置类型标签
const getConfigTypeLabel = (type) => {
  const typeMap = {
    'STRING': '字符串',
    'NUMBER': '数字',
    'BOOLEAN': '布尔值',
    'DICT': '字典',
    'LIST': '列表'
  }
  return typeMap[type] || type
}

// 获取标签类型
const getTypeTagType = (type) => {
  const typeMap = {
    'STRING': '',  // 空字符串会导致警告，改为 undefined 或默认值
    'NUMBER': 'success',
    'BOOLEAN': 'warning',
    'DICT': 'info',
    'LIST': 'primary'
  }
  return typeMap[type] || ''  // 如果是空字符串，则不设置 type 属性
}

// 打开编辑对话框
const openEditDialog = (row) => {
  Object.assign(configForm, {
    id: row.id,
    key: row.key,
    value: row.value,
    desc: row.desc,
    type: row.type,
    required: row.required
  })
  if (row.required || row.value) {
    updateValuePreview(row.value, row.type)
  }
  dialogVisible.value = true
}

// 处理对话框关闭
const handleDialogClose = (done) => {
  ElMessageBox.confirm('确定要关闭对话框吗？未保存的更改将会丢失。')
    .then(() => {
      done()
    })
    .catch(() => {
      // 用户取消关闭
    })
}

// 处理值输入
const handleValueInput = (newValue) => {
  if (configForm.required || newValue) {
    updateValuePreview(newValue, configForm.type)
  }
}

// 重置值预览
const resetValuePreview = () => {
  valuePreview.value = ''
  isValueTypeValid.value = true
  valueTypeCheckMessage.value = '非必填项，值可以为空'
}

// 检查字符串是否包含中文引号或英文引号
const checkStringQuotes = (value) => {
  const chineseQuotes = /[“”‘’]/;
  const englishQuotes = /["']/;

  if (chineseQuotes.test(value)) {
    return '错误: 字符串不能包含中文引号（“”‘’）';
  }

  if (englishQuotes.test(value)) {
    return '错误: 字符串不能包含英文引号（\'"）';
  }

  return null;
}

// 更新值预览
const updateValuePreview = (value, type) => {
  valuePreview.value = value || ''

  if (!value) {
    isValueTypeValid.value = true;
    valueTypeCheckMessage.value = '非必填项，值可以为空';
    return;
  }

  try {
    switch (type) {
      case 'STRING':
        const quoteError = checkStringQuotes(value);
        if (quoteError) {
          isValueTypeValid.value = false;
          valueTypeCheckMessage.value = quoteError;
        } else {
          isValueTypeValid.value = true;
          valueTypeCheckMessage.value = '字符串类型 ✓';
        }
        break;
      case 'NUMBER':
        const num = Number(value);
        if (isNaN(num)) {
          isValueTypeValid.value = false;
          valueTypeCheckMessage.value = '错误: 不是有效的数字';
        } else {
          isValueTypeValid.value = true;
          valueTypeCheckMessage.value = `数字类型 ✓ 解析为: ${num}`;
        }
        break;
      case 'BOOLEAN':
        if (value === 'true' || value === 'false') {
          isValueTypeValid.value = true;
          valueTypeCheckMessage.value = `布尔类型 ✓ 解析为: ${value === 'true'}`;
        } else {
          isValueTypeValid.value = false;
          valueTypeCheckMessage.value = '错误: 布尔值必须是 "true" 或 "false"';
        }
        break;
      case 'DICT':
      case 'LIST':
        JSON.parse(value);
        isValueTypeValid.value = true;
        valueTypeCheckMessage.value = `${type === 'DICT' ? '字典' : '列表'}类型 ✓`;
        break;
      default:
        isValueTypeValid.value = true;
        valueTypeCheckMessage.value = '未知类型';
    }
  } catch (e) {
    isValueTypeValid.value = false;
    if (type === 'DICT' || type === 'LIST') {
      valueTypeCheckMessage.value = `错误: 无效的JSON格式 - ${e.message}`;
    } else {
      valueTypeCheckMessage.value = `错误: 类型不匹配 - ${e.message}`;
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  // 如果是必填项但没有值，则不允许提交
  if (configForm.required && !configForm.value) {
    ElMessage.error('此配置项为必填项，值不能为空');
    return;
  }

  if ((configForm.required || configForm.value) && !isValueTypeValid.value) {
    ElMessage.error('值类型不匹配，请修正后再提交');
    return;
  }

  try {
    await configFormRef.value.validate();
    submitLoading.value = true;

    // 对特定键名的值进行处理，去除末尾的斜杠
    let valueToSubmit = configForm.value;
    if ((configForm.key === 'GITLAB_API_URL' || configForm.key === 'SERVER_DOMAIN') && valueToSubmit) {
      // 去除末尾的一个或多个斜杠
      valueToSubmit = valueToSubmit.replace(/\/+$/, '');
    }

    const res = await updateSystemConfig({
      config_id: configForm.id,
      key: configForm.key,
      value: valueToSubmit,
      desc: configForm.desc,
      type: configForm.type,
      required: configForm.required
    });

    if (res.code === 0) {
      ElMessage.success('更新成功');
      dialogVisible.value = false;
      fetchConfigList();

      // 如果是SERVER_DOMAIN配置项，检查域名是否可访问
      if (configForm.key === 'SERVER_DOMAIN') {
        await checkServerDomain(valueToSubmit);
      }
    } else {
      ElMessage.error(res.message || '更新失败');
    }
  } catch (error) {
    if (error.message === '无权限访问') {
      hasPermission.value = false
    } else {
      ElMessage.error('更新失败: ' + error.message)
    }
  } finally {
    submitLoading.value = false
  }
}




// 检查SERVER_DOMAIN域名是否可访问
const checkServerDomain = async (domain) => {
  try {
    // 确保域名以http://或https://开头
    let url = domain;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://' + url;
    }

    // 创建 AbortController 用于超时控制
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时

    try {
      // 发起GET请求检查域名是否可访问
      const response = await fetch(url, {
        method: 'GET',
        signal: controller.signal // 使用 signal 控制请求
      });

      // 清除超时定时器
      clearTimeout(timeoutId);

      // 查找SERVER_DOMAIN配置项的ID
      const serverDomainConfig = configList.value.find(config => config.key === 'SERVER_DOMAIN');
      const serverDomainConfigId = serverDomainConfig ? serverDomainConfig.id : null;

      if (serverDomainConfigId) {
        // 域名可访问，更新verified字段为true
        await updateSystemConfig({
          config_id: serverDomainConfigId,
          verified: true
        });

        // 重新获取配置列表以更新verified状态
        await fetchConfigList();
      }

      ElMessageBox.alert(
        `域名 ${domain} 可访问！状态码: ${response.status}`,
        '域名检查结果',
        {
          type: 'success',
          confirmButtonText: '确定'
        }
      );
    } catch (fetchError) {
      // 清除超时定时器
      clearTimeout(timeoutId);

      // 查找SERVER_DOMAIN配置项的ID
      const serverDomainConfig = configList.value.find(config => config.key === 'SERVER_DOMAIN');
      const serverDomainConfigId = serverDomainConfig ? serverDomainConfig.id : null;

      if (serverDomainConfigId) {
        // 域名不可访问，更新verified字段为false
        await updateSystemConfig({
          config_id: serverDomainConfigId,
          verified: false
        });

        // 重新获取配置列表以更新verified状态
        await fetchConfigList();
      }

      // 检查是否是超时错误
      let errorMessage = '';
      if (fetchError.name === 'AbortError') {
        errorMessage = '请求超时（超过5秒）';
      } else {
        errorMessage = fetchError.message;
      }

      throw new Error(errorMessage);
    }
  } catch (error) {
    ElMessageBox.alert(
      `域名 ${domain} 无法访问，请检查配置`,
      '域名检查结果',
      {
        type: 'error',
        dangerouslyUseHTMLString: true,
        confirmButtonText: '确定'
      }
    );
  }
}


// 分页相关
const handleSizeChange = (val) => {
  pagination.pageSize = val;
  pagination.currentPage = 1;
  fetchConfigList();
}

const handleCurrentChange = (val) => {
  pagination.currentPage = val;
  fetchConfigList();
}

// 返回首页
const goToHome = () => {
  router.push('/')
}
</script>

<style scoped>
.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  padding: 15px 20px;
  margin-bottom: 15px;
  border: 1px solid #ebeef5;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

.header-left p {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: #7f8c8d;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.admins-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admins-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.admins-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: 8px;
}

.admin-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.lock-icon {
  font-size: 12px;
}

.add-admin-btn {
  border-radius: 12px;
  transition: all 0.3s ease;
  font-weight: 600;
  height: 42px;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
}

.add-admin-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
}

.system-config-container {
  background: #f5f7fa;
}

.main-content {
  flex: 1;
  overflow: hidden;
}

.page-header {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  padding: 15px 20px;
  margin-bottom: 15px;
  border: 1px solid #ebeef5;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

.header-left p {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: #7f8c8d;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.admins-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admins-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.admins-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: 8px;
}

.admin-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.lock-icon {
  font-size: 12px;
}

.add-admin-btn {
  border-radius: 12px;
  transition: all 0.3s ease;
  font-weight: 600;
  height: 42px;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
}

.add-admin-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
}

.table-container {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}

.config-table {
  border: none;
  flex: 1;
}

/* 标签样式 */
:deep(.type-tag),
:deep(.status-tag) {
  font-size: 13px;
  padding: 6px 14px;
  border-radius: 24px;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  font-weight: 600;
}

:deep(.type-tag:hover),
:deep(.status-tag:hover) {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

/* 文本样式 */
.key-text {
  font-weight: 700;
  color: #667eea;
  font-size: 14px;
  padding: 4px 10px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 20px;
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.value-cell {
  max-width: 200px;
  margin: 0 auto;
}

.value-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
  color: #2c3e50;
  font-weight: 500;
  transition: all 0.3s ease;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(102, 126, 234, 0.05);
}

.value-text:hover {
  color: #667eea;
  background-color: rgba(102, 126, 234, 0.15);
  transform: translateX(5px);
}

.desc-cell {
  max-width: 250px;
  margin: 0 auto;
}

.desc-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
  color: #606266;
  font-weight: 500;
  transition: all 0.3s ease;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(102, 126, 234, 0.05);
}

.desc-text:hover {
  color: #667eea;
  background-color: rgba(102, 126, 234, 0.15);
  transform: translateX(5px);
}

.time-text {
  color: #7f8c8d;
  font-size: 14px;
}

.action-cell {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.action-button {
  padding: 6px 10px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.action-button:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

/* 弹窗美化核心样式 */
:deep(.config-dialog) {
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.15) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  width: 550px !important;
}

:deep(.config-dialog .el-dialog__header) {
  display: none;
}

:deep(.config-dialog .dialog-header) {
  padding: 20px 25px;
  border-bottom: 1px solid #f0f2f5;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  margin: -20px -25px 20px -25px;
  border-radius: 12px 12px 0 0;
}

:deep(.config-dialog .dialog-title) {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  letter-spacing: 0.3px;
}

:deep(.config-dialog .config-form) {
  padding: 0 15px;
}

:deep(.config-dialog .el-form-item) {
  margin-bottom: 20px;
  transition: all 0.2s ease;
  border-radius: 10px;
  padding: 10px;
}

:deep(.config-dialog .el-form-item:hover) {
  transform: translateX(3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

:deep(.config-dialog .el-form-item__label) {
  font-size: 14px;
  padding: 0 10px 6px 0;
  text-align: right;
  color: #475569;
  font-weight: 500;
}

:deep(.config-dialog .el-form-item__label .el-form-item__label-required) {
  color: #ef4444;
  margin-right: 3px;
}

/* 输入框美化 */
:deep(.config-dialog .form-input .el-input__wrapper),
:deep(.config-dialog .form-select .el-select__wrapper),
:deep(.config-dialog .form-textarea .el-textarea__inner) {
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) inset;
  transition: all 0.25s ease;
  height: 42px;
}

:deep(.config-dialog .form-input .el-input__wrapper:hover),
:deep(.config-dialog .form-select .el-select__wrapper:hover),
:deep(.config-dialog .form-textarea .el-textarea__inner:hover) {
  border-color: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.1);
}

:deep(.config-dialog .form-input .el-input__wrapper.is-focus),
:deep(.config-dialog .form-select .el-select__wrapper.is-focused),
:deep(.config-dialog .form-textarea .el-textarea__inner:focus) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  outline: none;
}

:deep(.config-dialog .el-textarea__inner) {
  min-height: 90px !important;
  resize: vertical;
  line-height: 1.6;
  font-size: 14px;
  border-radius: 8px;
}

/* 底部按钮区域 */
:deep(.config-dialog .dialog-footer) {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 25px 25px;
  border-top: 1px solid #f0f2f5;
  background-color: #f8fafc;
  margin: 15px -25px -25px -25px;
  border-radius: 0 0 12px 12px;
}

:deep(.config-dialog .footer-button) {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

:deep(.config-dialog .cancel-button) {
  border: 1px solid #e2e8f0;
  color: #475569;
  background-color: #ffffff;
}

:deep(.config-dialog .cancel-button:hover) {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
  transform: translateY(-2px);
}

:deep(.config-dialog .confirm-button) {
  background-color: #667eea;
  border-color: #667eea;
  color: white;
}

:deep(.config-dialog .confirm-button:hover) {
  background-color: #5a6fd8;
  border-color: #5a6fd8;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

:deep(.config-dialog .confirm-button:active) {
  transform: translateY(0);
}

/* 表单验证错误样式优化 */
:deep(.el-form-item.is-error .el-input__wrapper),
:deep(.el-form-item.is-error .el-select__wrapper),
:deep(.el-form-item.is-error .el-textarea__inner) {
  border-color: #ef4444 !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15) !important;
}

:deep(.el-form-item__error) {
  font-size: 12px;
  color: #ef4444;
  margin-top: 4px;
  padding-left: 2px;
}

.sc-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }

/* 响应式调整 */
@media (max-width: 768px) {
  :deep(.config-dialog) {
    width: 95% !important;
  }

  :deep(.config-dialog .el-form-item__label) {
    text-align: left;
    padding-bottom: 5px;
    display: block;
  }
}

.no-permission-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f8f9fa;
}

.no-permission-content {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.no-permission-icon {
  font-size: 64px;
  color: #f56c6c;
  margin-bottom: 20px;
}

.no-permission-content h2 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 24px;
}

.no-permission-content p {
  margin: 0 0 20px 0;
  color: #606266;
  font-size: 16px;
}
</style>

