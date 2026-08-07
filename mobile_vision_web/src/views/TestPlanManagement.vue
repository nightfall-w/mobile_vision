<template>
  <div class="testplan-management">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <div class="page-header">
        <div class="ttl-title-group">
          <div class="ttl-icon-wrap"><el-icon :size="18"><Calendar /></el-icon></div>
          <div>
            <h1 class="page-title">测试计划</h1>
            <p class="page-subtitle">管理工作空间下的测试计划</p>
          </div>
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
        :cell-style="{ textAlign: 'center' }"
        :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
        stripe
        empty-text="暂无测试计划"
        height="100%"
      >
        <el-table-column label="ID" width="64">
          <template #default="{ row }">
            <span class="id-text">#{{ row.plan_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="计划名称" min-width="130" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="100" show-overflow-tooltip />
        <el-table-column prop="case_count" label="用例数" width="70" />
        <el-table-column label="定时执行" min-width="130">
          <template #default="{ row }">
            <el-tooltip v-if="row.enable_schedule && row.schedule_cron_expression"
                        :content="row.schedule_cron_expression" placement="top">
              <el-tag type="success" size="small" effect="plain" round>
                {{ describeCron(row.schedule_cron_expression) }}
              </el-tag>
            </el-tooltip>
            <span v-else class="schedule-off">未启用</span>
          </template>
        </el-table-column>
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
    </div>

    <div class="tpm-page-footer">
      <el-pagination
        :current-page="pageNum"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        background
        small
      />
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

        <div class="sched-block">
          <div class="sched-switch-row">
            <div>
              <div class="sched-title">定时执行</div>
              <div class="sched-desc">按周期自动执行本计划，无需人工触发</div>
            </div>
            <el-switch v-model="form.enable_schedule" />
          </div>

          <template v-if="form.enable_schedule">
            <!-- ── 简单模式：按频率类型配置，cron 由界面生成 ── -->
            <template v-if="!advancedMode">
              <div class="sched-row">
                <span class="sched-label">执行频率</span>
                <el-radio-group v-model="sched.freq" size="small">
                  <el-radio-button v-for="f in FREQ_OPTIONS" :key="f.value" :value="f.value">
                    {{ f.label }}
                  </el-radio-button>
                </el-radio-group>
              </div>

              <!-- 按分钟 / 按小时：间隔 -->
              <div v-if="sched.freq === FREQ.MINUTE || sched.freq === FREQ.HOURLY" class="sched-row">
                <span class="sched-label">每隔</span>
                <el-input-number
                  v-model="sched.interval"
                  :min="1"
                  :max="sched.freq === FREQ.MINUTE ? 59 : 23"
                  size="small"
                  controls-position="right"
                  style="width: 110px"
                />
                <span class="sched-unit">{{ sched.freq === FREQ.MINUTE ? '分钟' : '小时' }}执行一次</span>
              </div>

              <!-- 每周：星期多选 -->
              <div v-if="sched.freq === FREQ.WEEKLY" class="sched-row">
                <span class="sched-label">星期</span>
                <div class="weekday-group">
                  <button
                    v-for="w in WEEKDAY_OPTIONS"
                    :key="w.value"
                    type="button"
                    class="weekday-btn"
                    :class="{ active: sched.weekdays.includes(w.value) }"
                    @click="toggleWeekday(w.value)"
                  >{{ w.label }}</button>
                </div>
              </div>

              <!-- 每月：日期多选 -->
              <div v-if="sched.freq === FREQ.MONTHLY" class="sched-row">
                <span class="sched-label">日期</span>
                <el-select v-model="sched.monthDays" multiple collapse-tags collapse-tags-tooltip
                           size="small" placeholder="选择日期" style="flex: 1">
                  <el-option v-for="d in 31" :key="d" :label="`${d} 日`" :value="d" />
                </el-select>
              </div>

              <!-- 固定时刻（按分钟模式无需选时刻） -->
              <div v-if="sched.freq !== FREQ.MINUTE" class="sched-row">
                <span class="sched-label">{{ sched.freq === FREQ.HOURLY ? '第几分钟' : '执行时间' }}</span>
                <el-time-picker
                  v-if="sched.freq !== FREQ.HOURLY"
                  v-model="schedTime"
                  format="HH:mm"
                  value-format="HH:mm"
                  placeholder="选择时间"
                  size="small"
                  style="width: 130px"
                />
                <template v-else>
                  <el-input-number v-model="schedMinuteOfHour" :min="0" :max="59" size="small"
                                   controls-position="right" style="width: 110px" />
                  <span class="sched-unit">分</span>
                </template>
              </div>
            </template>

            <!-- ── 高级模式：按 cron 字段配置 + 原始表达式 ── -->
            <template v-else>
              <el-tabs v-model="activeCronField" class="cron-tabs">
                <el-tab-pane v-for="(f, i) in CRON_FIELD_DEFS" :key="f.key" :label="f.label" :name="f.key" />
              </el-tabs>

              <div class="cron-field-editor">
                <div class="cron-field-desc">正在配置【{{ currentCronField.label }}】的执行规则</div>
                <el-radio-group v-model="fieldRules[activeCronField].type" size="small" class="cron-rule-group">
                  <el-radio value="all">所有值（*）</el-radio>
                  <el-radio value="range">范围（a-b）</el-radio>
                  <el-radio value="interval">间隔（a/b）</el-radio>
                  <el-radio value="specific">指定值（a,b,c）</el-radio>
                </el-radio-group>

                <div v-if="fieldRules[activeCronField].type === 'range'" class="cron-rule-fields">
                  <span>从</span>
                  <el-input-number v-model="fieldRules[activeCronField].rangeStart"
                                   :min="currentCronField.min" :max="currentCronField.max"
                                   size="small" controls-position="right" style="width: 100px" />
                  <span>到</span>
                  <el-input-number v-model="fieldRules[activeCronField].rangeEnd"
                                   :min="currentCronField.min" :max="currentCronField.max"
                                   size="small" controls-position="right" style="width: 100px" />
                  <span class="sched-unit">{{ currentCronField.unit }}</span>
                </div>

                <div v-if="fieldRules[activeCronField].type === 'interval'" class="cron-rule-fields">
                  <span>从</span>
                  <el-input-number v-model="fieldRules[activeCronField].intervalStart"
                                   :min="currentCronField.min" :max="currentCronField.max"
                                   size="small" controls-position="right" style="width: 100px" />
                  <span>开始，每</span>
                  <el-input-number v-model="fieldRules[activeCronField].intervalStep"
                                   :min="1" :max="currentCronField.max"
                                   size="small" controls-position="right" style="width: 100px" />
                  <span class="sched-unit">{{ currentCronField.unit }}一次</span>
                </div>

                <div v-if="fieldRules[activeCronField].type === 'specific'" class="cron-rule-fields">
                  <el-select v-model="fieldRules[activeCronField].specificValues" multiple
                             collapse-tags collapse-tags-tooltip size="small"
                             placeholder="选择具体值" style="flex: 1">
                    <el-option v-for="v in currentCronFieldValues" :key="v.value"
                               :label="v.label" :value="v.value" />
                  </el-select>
                </div>

                <div v-if="fieldRules[activeCronField].type === 'all'" class="cron-hint">
                  {{ currentCronField.allHint }}
                </div>
              </div>

              <div class="sched-row cron-raw-row">
                <span class="sched-label">表达式</span>
                <el-input v-model="form.schedule_cron_expression" size="small"
                          placeholder="0 0 2 * * *" @input="handleRawCronInput" />
              </div>
            </template>

            <!-- ── 结果区：人话描述 + 表达式 + 模式切换 + 执行时间预览 ── -->
            <div class="cron-result">
              <div class="cron-result-head">
                <div class="cron-result-desc">
                  <el-icon><Calendar /></el-icon>
                  <span>{{ cronError ? '表达式无效' : describeCron(form.schedule_cron_expression) }}</span>
                </div>
                <button type="button" class="cron-mode-btn" @click="toggleAdvancedMode">
                  {{ advancedMode ? '返回简单模式' : '高级设置' }}
                </button>
              </div>

              <div class="cron-segs">
                <span v-for="(seg, i) in splitCron(form.schedule_cron_expression)" :key="i" class="cron-seg">
                  <b>{{ seg }}</b><i>{{ CRON_FIELD_LABELS[i] }}</i>
                </span>
              </div>

              <div v-if="cronError" class="cron-error">{{ cronError }}</div>
              <template v-else-if="cronNextTimes.length">
                <div class="cron-preview-label">接下来 {{ cronNextTimes.length }} 次执行</div>
                <div v-for="(t, i) in cronNextTimes" :key="i" class="cron-time">{{ t }}</div>
              </template>
            </div>
          </template>
        </div>

        <!-- ── 通知配置 ── -->
        <div class="sched-block" style="margin-top: 12px;">
          <div class="sched-switch-row">
            <div>
              <div class="sched-title">消息通知</div>
              <div class="sched-desc">任务完成后通过机器人推送结果到团队协作平台</div>
            </div>
            <el-switch v-model="form.enable_notification" />
          </div>

          <template v-if="form.enable_notification">
            <el-checkbox v-model="form.notify_on_failure_only" style="margin-top: 10px; font-size: 13px;">
              仅失败时通知
            </el-checkbox>

            <div class="notif-row">
              <span class="sched-label">企业微信</span>
              <el-input v-model="form.wecom_webhooks" type="textarea" :rows="2"
                        placeholder="多个 webhook URL 请每行一个" />
            </div>
            <div class="notif-row">
              <span class="sched-label">飞书</span>
              <el-input v-model="form.lark_webhooks" type="textarea" :rows="2"
                        placeholder="多个 webhook URL 请每行一个" />
            </div>
            <div class="notif-row">
              <span class="sched-label">钉钉</span>
              <el-input v-model="form.dingtalk_webhooks" type="textarea" :rows="2"
                        placeholder="多个 webhook URL 请每行一个" />
            </div>
          </template>
        </div>
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

    <el-drawer
      v-model="addCaseDialogVisible"
      size="85%"
      direction="rtl"
      class="case-drawer"
      @open="handleDialogOpen"
      @close="handleDialogClose"
      destroy-on-close
    >
      <template #header>
        <div class="drawer-header">
          <div class="drawer-header-left">
            <div class="drawer-header-icon">
              <el-icon :size="18"><DocumentAdd /></el-icon>
            </div>
            <div class="drawer-header-text">
              <div class="drawer-header-title">关联测试用例</div>
              <div class="drawer-header-subtitle">{{ selectedPlan?.name }} · 配置计划执行的用例与设备</div>
            </div>
          </div>
          <div class="drawer-header-right">
            <el-tag size="small" type="info" effect="plain" class="drawer-header-tag">
              已关联 {{ associatedCaseList.length }} 个用例
            </el-tag>
          </div>
        </div>
      </template>
      <el-tabs v-model="activeTab" class="case-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="已关联用例" name="associated">
          <div class="associated-case-tab">
            <div class="associated-header">
              <div class="associated-stats">
                <div class="stat-item stat-total">
                  <span class="stat-num">{{ associatedCaseList.length }}</span>
                  <span class="stat-label">全部用例</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item stat-specified">
                  <span class="stat-num">{{ specifiedDeviceCount }}</span>
                  <span class="stat-label">指定设备</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item stat-dynamic">
                  <span class="stat-num">{{ dynamicAssignCount }}</span>
                  <span class="stat-label">动态分配</span>
                </div>
              </div>
              <div class="associated-actions">
                <el-button type="primary" plain size="small" @click="openBatchEditRelationDialog" :disabled="selectedToRemove.length === 0">
                  <el-icon :size="13"><Setting /></el-icon>
                  批量修改 ({{ selectedToRemove.length }})
                </el-button>
                <el-button type="danger" size="small" @click="batchRemoveRelations" :disabled="selectedToRemove.length === 0">
                  <el-icon :size="13"><Delete /></el-icon>
                  批量删除 ({{ selectedToRemove.length }})
                </el-button>
              </div>
            </div>
            <div class="case-table-wrap">
            <el-table
              ref="associatedTableRef"
              :data="associatedCaseList"
              @selection-change="handleAssociatedSelectionChange"
              class="case-table"
              stripe
              style="width: 100%"
              height="100%"
            >
              <el-table-column type="selection" width="50" />
              <el-table-column prop="case_name" label="用例名称" min-width="180" show-overflow-tooltip />
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
                  <span class="config-text">{{ row.llm_name || getLLMName(row.llm_credential_id) || '-' }}</span>
                  <el-tag v-if="row.llm_credential_id && row.llm_is_active === false" size="small" type="danger" effect="plain" class="llm-disabled-tag">
                    {{ llmUnavailableText(row.llm_unavailable_reason) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="YOLO" width="200">
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
          </div>
        </el-tab-pane>
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
            <div class="case-table-wrap">
            <el-table
              ref="addTableRef"
              :data="availableCaseList"
              v-loading="caseLoading"
              @selection-change="handleSelectionChange"
              class="case-table"
              stripe
              style="width: 100%"
              height="100%"
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
            </div>
            <div v-if="selectedToAdd.length > 0" class="batch-config">
              <div class="batch-config-header">
                <div class="batch-config-badge">{{ selectedToAdd.length }}</div>
                <span>已选 <strong>{{ selectedToAdd.length }}</strong> 个用例</span>
                <span class="batch-config-sep">|</span>
                <span class="batch-config-hint">统一配置以下参数后批量添加</span>
              </div>
              <div class="batch-config-fields">
                <el-select v-model="batchDeviceId" placeholder="执行设备" size="default" style="width: 200px">
                  <el-option label="🔄 动态分配（空闲设备）" :value="''" />
                  <el-option v-for="d in deviceOptions" :key="d.id" :label="`${d.brand} ${d.model} (${d.id})`" :value="d.id" />
                </el-select>
                <el-select v-model="batchLLMId" placeholder="选择LLM" size="default" style="width: 180px">
                  <el-option v-for="l in llmOptions" :key="l.id" :label="`${l.model} (${l.base_url || 'N/A'})`" :value="l.id" />
                </el-select>
                <el-select v-model="batchYOLOId" placeholder="选择YOLO" size="default" style="width: 130px">
                  <el-option v-for="y in yoloOptions" :key="y.id" :label="y.name" :value="y.id" />
                </el-select>
                <el-button type="primary" @click="batchAddCases" size="default">
                  添加 ({{ selectedToAdd.length }})
                </el-button>
              </div>
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
      </el-tabs>
    </el-drawer>

    <!-- 编辑关联用例配置弹窗 -->
    <el-dialog
      v-model="editRelationDialogVisible"
      width="640px"
      class="er-dialog"
      destroy-on-close
      align-center
      @close="editRelationBatchMode = false"
    >
      <template #header>
        <div class="er-header">
          <div class="er-header-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="er-header-text">
            <div class="er-header-title">{{ editRelationBatchMode ? '批量修改配置' : '编辑用例配置' }}</div>
            <div class="er-header-subtitle">
              {{ editRelationBatchMode ? `已选 ${selectedToRemove.length} 个用例，保存后统一应用` : '为该用例单独覆盖计划默认配置' }}
            </div>
          </div>
        </div>
      </template>

      <div class="er-case-card">
        <template v-if="editRelationBatchMode">
          <div class="er-case-card-name">已选 {{ selectedToRemove.length }} 个用例</div>
          <div class="er-case-card-meta">
            <el-tag size="small" type="primary" effect="light" round>批量修改</el-tag>
          </div>
        </template>
        <template v-else>
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
        </template>
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
                  v-for="l in editRelationLLMOptions"
                  :key="l.id"
                  :label="l.label"
                  :value="l.id"
                  :disabled="l.disabled"
                />
              </el-select>
              <div v-if="editRelationForm.llm_credential_id && editRelationForm.llm_is_active === false" class="er-field-warning">
                {{ llmWarningText }}
              </div>
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
          <el-button type="primary" @click="confirmEditRelation">{{ editRelationBatchMode ? '批量修改' : '保存配置' }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh, Warning, User, InfoFilled, Iphone, Edit, Delete, Setting, Document, DocumentAdd, MagicStick, Cpu, Check, Monitor, Aim, TrendCharts, Calendar } from '@element-plus/icons-vue'
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
  getWorkspaceLLMCredentials,
  getModelsList,
  getTestCaseList,
  getWorkspaceDetail
} from '@/network/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  FREQ,
  FREQ_OPTIONS,
  WEEKDAY_OPTIONS,
  configToCron,
  cronToConfig,
  defaultScheduleConfig,
  describeCron,
  nextRunTimes,
  splitCron,
  validateCron,
} from '@/utils/cron.js'

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
const editRelationBatchMode = ref(false)  // 编辑弹窗是否处于批量修改模式
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
  status: '',
  llm_name: '',
  llm_is_active: true,
  llm_unavailable_reason: null
})

// 凭证不可用原因的展示文案
const LLM_UNAVAILABLE_TEXT = {
  disabled: '已禁用',
  deleted: '已删除',
  missing: '凭证不存在',
  foreign: '非本空间'
}

const llmUnavailableText = (reason) => LLM_UNAVAILABLE_TEXT[reason] || '不可用'

// 编辑弹窗中不可用凭证的提示语，按原因给出不同说明
const LLM_WARNING_TEXT = {
  disabled: '原凭证已被禁用，请重新选择一个可用的 LLM',
  deleted: '原凭证已被删除，请重新选择一个可用的 LLM',
  missing: '原凭证不存在，请重新选择一个可用的 LLM',
  foreign: '原凭证不属于当前工作空间，请重新选择一个可用的 LLM'
}

const llmWarningText = computed(
  () => LLM_WARNING_TEXT[editRelationForm.llm_unavailable_reason] || '原凭证不可用，请重新选择一个可用的 LLM'
)

// 编辑弹窗的LLM下拉：llmOptions 只含本空间（含系统级）的可用凭证，
// 若当前关联的凭证不可用，则额外注入一条 disabled 项，让用户看得见原配置但无法再次选中
const editRelationLLMOptions = computed(() => {
  const options = llmOptions.value.map(l => ({
    id: l.id,
    label: `${l.model} (${l.base_url || 'N/A'})`,
    disabled: false
  }))
  const currentId = editRelationForm.llm_credential_id
  if (currentId && !options.some(o => o.id === currentId)) {
    const name = editRelationForm.llm_name || currentId
    const tip = llmUnavailableText(editRelationForm.llm_unavailable_reason)
    options.unshift({ id: currentId, label: `${name}（${tip}）`, disabled: true })
  }
  return options
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
  description: '',
  enable_schedule: false,
  schedule_cron_expression: '',
  enable_notification: false,
  notify_on_failure_only: false,
  wecom_webhooks: '',
  lark_webhooks: '',
  dingtalk_webhooks: ''
})

const CRON_FIELD_LABELS = ['秒', '分', '时', '日', '月', '周']

// ── 定时配置：简单模式（频率驱动） ──
const advancedMode = ref(false)
const sched = reactive(defaultScheduleConfig())

// 时刻用独立 ref 桥接 el-time-picker（其 value-format 为 'HH:mm'）
const schedTime = computed({
  get: () => sched.time,
  set: v => { sched.time = v || '00:00' },
})
// 按小时模式只需"第几分钟"
const schedMinuteOfHour = computed({
  get: () => parseInt((sched.time || '00:00').split(':')[1], 10) || 0,
  set: v => { sched.time = `00:${String(v ?? 0).padStart(2, '0')}` },
})

const toggleWeekday = (v) => {
  const i = sched.weekdays.indexOf(v)
  if (i >= 0) {
    // 至少保留一个星期，否则表达式无意义
    if (sched.weekdays.length > 1) sched.weekdays.splice(i, 1)
  } else {
    sched.weekdays.push(v)
  }
}

// 简单模式下配置变化即重新生成表达式
watch(sched, () => {
  if (form.enable_schedule && !advancedMode.value) {
    form.schedule_cron_expression = configToCron(sched)
  }
}, { deep: true })

// ── 定时配置：高级模式（按 cron 字段） ──
const CRON_FIELD_DEFS = [
  { key: 'second', label: '秒', idx: 0, min: 0, max: 59, unit: '秒', allHint: '每秒都会执行' },
  { key: 'minute', label: '分', idx: 1, min: 0, max: 59, unit: '分', allHint: '每分钟都会执行' },
  { key: 'hour', label: '时', idx: 2, min: 0, max: 23, unit: '小时', allHint: '每小时都会执行' },
  { key: 'day', label: '日', idx: 3, min: 1, max: 31, unit: '日', allHint: '每天都会执行' },
  { key: 'month', label: '月', idx: 4, min: 1, max: 12, unit: '月', allHint: '每月都会执行' },
  { key: 'week', label: '周', idx: 5, min: 0, max: 6, unit: '', allHint: '每周每天都会执行' },
]
const activeCronField = ref('hour')
const currentCronField = computed(
  () => CRON_FIELD_DEFS.find(f => f.key === activeCronField.value) || CRON_FIELD_DEFS[2]
)
// 周字段的下拉展示中文（值仍按 APScheduler 约定 0=周一）
const currentCronFieldValues = computed(() => {
  const f = currentCronField.value
  if (f.key === 'week') return WEEKDAY_OPTIONS.map(w => ({ value: w.value, label: `周${w.label}` }))
  const arr = []
  for (let v = f.min; v <= f.max; v++) arr.push({ value: v, label: String(v) })
  return arr
})

const makeFieldRule = (f) => ({
  type: 'all',
  rangeStart: f.min, rangeEnd: f.max,
  intervalStart: f.min, intervalStep: 1,
  specificValues: [],
})
const fieldRules = reactive(
  Object.fromEntries(CRON_FIELD_DEFS.map(f => [f.key, makeFieldRule(f)]))
)

/** 单个字段规则 -> cron 片段 */
const ruleToSegment = (key) => {
  const r = fieldRules[key]
  switch (r.type) {
    case 'range':
      return `${r.rangeStart}-${r.rangeEnd}`
    case 'interval':
      return `${r.intervalStart}/${r.intervalStep}`
    case 'specific':
      return r.specificValues.length ? [...r.specificValues].sort((a, b) => a - b).join(',') : '*'
    case 'all':
    default:
      return '*'
  }
}

/** 由 6 个字段规则拼出完整表达式 */
const buildCronFromFields = () => CRON_FIELD_DEFS.map(f => ruleToSegment(f.key)).join(' ')

/** 反向：把表达式各段解析进字段规则，供进入高级模式时回填 */
const loadFieldsFromCron = (expression) => {
  const segs = splitCron(expression)
  CRON_FIELD_DEFS.forEach((f, i) => {
    const seg = segs[i]
    const r = fieldRules[f.key]
    Object.assign(r, makeFieldRule(f))
    if (seg === '*' || seg === '?') { r.type = 'all'; return }
    let m
    if ((m = seg.match(/^(\d+)-(\d+)$/))) {
      r.type = 'range'; r.rangeStart = +m[1]; r.rangeEnd = +m[2]
    } else if ((m = seg.match(/^(\*|\d+)\/(\d+)$/))) {
      r.type = 'interval'
      r.intervalStart = m[1] === '*' ? f.min : +m[1]
      r.intervalStep = +m[2]
    } else if (/^\d+(,\d+)*$/.test(seg)) {
      r.type = 'specific'; r.specificValues = seg.split(',').map(Number)
    } else {
      r.type = 'all'
    }
  })
}

// 高级模式下字段规则变化即重新生成表达式
watch(fieldRules, () => {
  if (form.enable_schedule && advancedMode.value) {
    form.schedule_cron_expression = buildCronFromFields()
  }
}, { deep: true })

/** 高级模式手输表达式时，同步回字段规则（保持 tab 面板与输入框一致） */
const handleRawCronInput = () => {
  loadFieldsFromCron(form.schedule_cron_expression)
}

/** 切换简单/高级模式，尽量保留当前表达式 */
const toggleAdvancedMode = () => {
  if (!advancedMode.value) {
    loadFieldsFromCron(form.schedule_cron_expression)
    advancedMode.value = true
  } else {
    const cfg = cronToConfig(form.schedule_cron_expression)
    if (cfg) {
      Object.assign(sched, cfg)
      advancedMode.value = false
    } else {
      // 当前表达式超出简单模式表达力，回退会丢配置，故提示后按原样重置
      ElMessage.warning('当前表达式较复杂，简单模式无法表示，已重置为每天 02:00')
      Object.assign(sched, defaultScheduleConfig())
      form.schedule_cron_expression = configToCron(sched)
      advancedMode.value = false
    }
  }
}

const cronCheck = computed(() => {
  if (!form.enable_schedule) return { times: [], error: '' }
  return nextRunTimes(form.schedule_cron_expression, 5)
})
const cronNextTimes = computed(() => cronCheck.value.times)
const cronError = computed(() => cronCheck.value.error)

/** 打开弹窗时按已有表达式决定用哪个模式，并回填对应配置 */
const initScheduleFromForm = () => {
  const expr = form.schedule_cron_expression
  if (!expr) {
    Object.assign(sched, defaultScheduleConfig())
    advancedMode.value = false
    form.schedule_cron_expression = configToCron(sched)
    loadFieldsFromCron(form.schedule_cron_expression)
    return
  }
  const cfg = cronToConfig(expr)
  if (cfg) {
    Object.assign(sched, cfg)
    advancedMode.value = false
  } else {
    // 简单模式表达不了 -> 直接进高级模式，避免静默改写用户的表达式
    advancedMode.value = true
  }
  loadFieldsFromCron(expr)
}

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

// 辅助：textarea 换行与后端数组互转
const toLines = (arr) => Array.isArray(arr) ? arr.join('\n') : (arr || '')
const fromLines = (str) => (str || '').split('\n').map(s => s.trim()).filter(Boolean)

const openCreateDialog = () => {
  dialogTitle.value = '创建测试计划'
  form.plan_id = null
  form.name = ''
  form.description = ''
  form.enable_schedule = false
  form.schedule_cron_expression = ''
  form.enable_notification = false
  form.notify_on_failure_only = false
  form.wecom_webhooks = ''
  form.lark_webhooks = ''
  form.dingtalk_webhooks = ''
  initScheduleFromForm()
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  dialogTitle.value = '编辑测试计划'
  form.plan_id = row.plan_id
  form.name = row.name
  form.description = row.description || ''
  form.enable_schedule = row.enable_schedule === true
  form.schedule_cron_expression = row.schedule_cron_expression || ''
  form.enable_notification = row.enable_notification === true
  form.notify_on_failure_only = row.notify_on_failure_only === true
  form.wecom_webhooks = toLines(row.wecom_webhooks)
  form.lark_webhooks = toLines(row.lark_webhooks)
  form.dingtalk_webhooks = toLines(row.dingtalk_webhooks)
  initScheduleFromForm()
  dialogVisible.value = true
}

const savePlan = async () => {
  if (!form.name) {
    ElMessage.error('请输入计划名称')
    return
  }
  if (form.enable_schedule) {
    const check = validateCron(form.schedule_cron_expression)
    if (!check.valid) {
      ElMessage.error(check.message)
      return
    }
  }

  const params = {
    name: form.name,
    description: form.description,
    workspace_id: workspaceId.value,
    enable_schedule: form.enable_schedule,
    // 关闭定时时传 null，后端据此移除定时任务
    schedule_cron_expression: form.enable_schedule ? form.schedule_cron_expression.trim() : null,
    enable_notification: form.enable_notification,
    notify_on_failure_only: form.notify_on_failure_only,
    wecom_webhooks: form.enable_notification ? fromLines(form.wecom_webhooks) : [],
    lark_webhooks: form.enable_notification ? fromLines(form.lark_webhooks) : [],
    dingtalk_webhooks: form.enable_notification ? fromLines(form.dingtalk_webhooks) : [],
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
  form.enable_schedule = false
  form.schedule_cron_expression = ''
  form.enable_notification = false
  form.notify_on_failure_only = false
  form.wecom_webhooks = ''
  form.lark_webhooks = ''
  form.dingtalk_webhooks = ''
}

const handleDialogOpen = async () => {
  activeTab.value = 'associated'
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
      // 仅取当前工作空间 + 系统级别的可用凭证（接口已过滤禁用与已删除）
      getWorkspaceLLMCredentials({ workspace_id: workspaceId.value }),
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

  if (!llmId) {
    ElMessage.error('LLM模型未加载完成')
    return
  }
  if (!yoloId) {
    try {
      await ElMessageBox.confirm(
        'YOLO模型未选择，在小程序或H5页面中将不能识别页面元素信息，是否继续？',
        '提示',
        { confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return
    }
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
  editRelationForm.llm_name = row.llm_name || ''
  editRelationForm.llm_is_active = row.llm_is_active !== false
  editRelationForm.llm_unavailable_reason = row.llm_unavailable_reason || null
  editRelationBatchMode.value = false
  editRelationDialogVisible.value = true
}

const openBatchEditRelationDialog = () => {
  const selected = selectedToRemove.value
  if (selected.length === 0) {
    ElMessage.warning('请先勾选要修改的用例')
    return
  }
  // 以第一条选中用例的当前配置作为批量表单的默认值
  const first = selected[0]
  editRelationForm.id = null
  editRelationForm.device_id = first.device_id || ''
  editRelationForm.device_name = first.device_name || ''
  editRelationForm.llm_credential_id = first.llm_credential_id || null
  editRelationForm.yolo_model_id = first.yolo_model_id || null
  editRelationForm.ocr_engine = first.ocr_engine || null
  editRelationForm.reasoning_effort = first.reasoning_effort || null
  editRelationForm.case_name = ''
  editRelationForm.case_level = ''
  editRelationForm.status = ''
  editRelationForm.llm_name = first.llm_name || ''
  editRelationForm.llm_is_active = first.llm_is_active !== false
  editRelationForm.llm_unavailable_reason = first.llm_unavailable_reason || null
  editRelationBatchMode.value = true
  editRelationDialogVisible.value = true
}

const confirmEditRelation = async () => {
  if (!editRelationForm.yolo_model_id) {
    try {
      await ElMessageBox.confirm(
        'YOLO模型未选择，在小程序或H5页面中将不能识别页面元素信息，是否继续？',
        '提示',
        { confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return
    }
  }

  const buildParams = (id) => {
    const params = {}
    if (id !== undefined) params.id = id
    if (editRelationForm.device_id !== undefined) params.device_id = editRelationForm.device_id
    if (editRelationForm.llm_credential_id !== undefined) params.llm_credential_id = editRelationForm.llm_credential_id
    if (editRelationForm.yolo_model_id !== undefined) params.yolo_model_id = editRelationForm.yolo_model_id
    if (editRelationForm.ocr_engine !== undefined) params.ocr_engine = editRelationForm.ocr_engine
    if (editRelationForm.reasoning_effort !== undefined) params.reasoning_effort = editRelationForm.reasoning_effort
    return params
  }

  try {
    if (editRelationBatchMode.value) {
      const selected = selectedToRemove.value
      if (selected.length === 0) {
        ElMessage.warning('请先勾选要修改的用例')
        return
      }
      for (const item of selected) {
        const result = await updateCaseRelation(buildParams(item.id))
        if (result.code !== 0) {
          ElMessage.error(`用例「${item.case_name || item.id}」更新失败：${result.message || '未知错误'}`)
          return
        }
      }
      editRelationDialogVisible.value = false
      await refreshAssociatedCases()
      selectedToRemove.value = []
      if (associatedTableRef.value) {
        associatedTableRef.value.clearSelection()
      }
      ElMessage.success(`批量更新 ${selected.length} 个用例成功`)
    } else {
      const result = await updateCaseRelation(buildParams(editRelationForm.id))
      if (result.code === 0) {
        ElMessage.success('更新成功')
        editRelationDialogVisible.value = false
        await refreshAssociatedCases()
      } else {
        ElMessage.error(result.message || '更新失败')
      }
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
      plan_id: row.plan_id,
      plan_name: row.name
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
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: #ffffff;
  border-radius: 12px;
}

.ttl-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ttl-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #eef2ff;
  color: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #1d1d1f;
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
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #ffffff;
  border-radius: 12px;
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
  flex: 1;
  min-height: 0;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  overflow: hidden;
}



.action-group {
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
}

.action-btn {
  border: none;
  border-radius: 6px;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.12s ease;
  font-weight: 500;
}

.action-edit { background: #eef2ff; color: #5b6ef7; }
.action-edit:hover { background: #dde3ff; }
.action-link { background: #ecfdf5; color: #059669; }
.action-link:hover { background: #d1fae5; }
.action-run { background: #fffbeb; color: #d97706; }
.action-run:hover { background: #fef3c7; }
.action-view { background: #eef2ff; color: #5b6ef7; }
.action-view:hover { background: #dde3ff; }
.action-delete { background: #fef2f2; color: #dc2626; }
.action-delete:hover { background: #fee2e2; }

.tpm-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }

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
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.add-case-tab,
.associated-case-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ml-2 {
  margin-left: 8px;
}

/* 表格包裹层：填满 tab 可用高度（底部由 drawer body padding 留 20px） */
.case-table-wrap {
  flex: 1;
  min-height: 200px;
  overflow: hidden;
  border-radius: 8px;
}

.case-table {
  border-radius: 8px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

/* ===== 关联用例 Drawer =====
   抽屉内容通过 <teleport> 挂到 body，.el-drawer 根元素不带组件的 scoped data 属性，
   因此对 Element Plus 内部元素的规则必须用 :global()，否则 :deep 编译后的
   `.case-drawer[data-v-xxx] .el-drawer__body` 永远匹配不上。 */
.case-drawer :global(.el-drawer__header) {
  padding: 20px 24px 16px;
  margin-bottom: 0;
  border-bottom: 1px solid #f0f0f0;
}

.case-drawer :global(.el-drawer__body) {
  padding: 0 20px 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.case-drawer .el-tabs {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.case-drawer :global(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding-bottom: 0;
}

.case-drawer :global(.el-tab-pane) {
  height: 100%;
  overflow-y: auto;
}

/* Drawer header */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 10px;
}

.drawer-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-header-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #eef2ff;
  color: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.drawer-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-header-title {
  font-size: 17px;
  font-weight: 700;
  color: #1d1d1f;
  letter-spacing: -0.3px;
}

.drawer-header-subtitle {
  font-size: 12.5px;
  color: #8e8e93;
}

.drawer-header-tag {
  background: #f0f4ff;
  color: #5b6ef7;
  border: 1px solid #dce3ff;
  border-radius: 6px;
  font-weight: 500;
}

/* 关联用例统计栏 */
.associated-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.associated-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.associated-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: #5b6ef7;
}

.stat-total .stat-num { color: #5b6ef7; }
.stat-specified .stat-num { color: #059669; }
.stat-dynamic .stat-num { color: #d97706; }

.stat-label {
  font-size: 13px;
  color: #6b7280;
}

.stat-divider {
  width: 1px;
  height: 20px;
  background: #e5e7eb;
}

/* 批量配置栏 */
.batch-config {
  background: #f8f9fc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 16px;
  animation: slideUp 0.2s ease-out;
}

.batch-config-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #4b5563;
}

.batch-config-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #5b6ef7;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.batch-config-sep {
  color: #d1d5db;
  font-size: 12px;
}

.batch-config-hint {
  color: #9ca3af;
  font-size: 12px;
}

.batch-config-fields {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
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

/* ─── 定时执行配置 ─── */
.sched-block {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
  background: #fafafa;
}

.sched-switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sched-title {
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
}

.sched-desc {
  font-size: 12px;
  color: #8e8e93;
  margin-top: 2px;
}

.sched-item {
  margin-top: 14px;
  margin-bottom: 0 !important;
}

/* 配置行：标签 + 控件横向排列 */
.sched-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.sched-label {
  font-size: 12px;
  color: #6b7280;
  min-width: 60px;
  flex-shrink: 0;
}

.sched-unit {
  font-size: 12px;
  color: #8e8e93;
}

/* 星期按钮组 */
.weekday-group {
  display: flex;
  gap: 6px;
}

.weekday-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #d2d2d7;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.weekday-btn:hover {
  border-color: #5b6ef7;
  color: #5b6ef7;
}

.weekday-btn.active {
  background: #5b6ef7;
  border-color: #5b6ef7;
  color: #fff;
  font-weight: 600;
}

/* 高级模式：字段 tab 与规则编辑 */
.cron-tabs {
  margin-top: 12px;
}

.cron-tabs :deep(.el-tabs__header) {
  margin-bottom: 10px;
}

.cron-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 0 14px;
}

.cron-field-editor {
  padding: 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #eee;
}

.cron-field-desc {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 10px;
}

.cron-rule-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
}

.cron-rule-group :deep(.el-radio) {
  margin-right: 0;
  height: 26px;
}

.cron-rule-fields {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #6b7280;
  flex-wrap: wrap;
}

.cron-raw-row {
  margin-top: 12px;
}

/* 结果区 */
.cron-result {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #eee;
}

.cron-result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.cron-result-desc {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
}

.cron-result-desc .el-icon {
  color: #5b6ef7;
}

.cron-mode-btn {
  border: none;
  background: transparent;
  color: #5b6ef7;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  flex-shrink: 0;
}

.cron-mode-btn:hover {
  background: #eef2ff;
}

.cron-segs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.schedule-off {
  font-size: 12px;
  color: #c0c4cc;
}

/* ─── 通知配置 ─── */
.notif-row {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 12px;
}

.notif-row .sched-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.cron-fields {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.cron-seg {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 40px;
  padding: 3px 6px;
  border-radius: 6px;
  background: #eef2ff;
}

.cron-seg b {
  font-family: monospace;
  font-size: 12px;
  color: #5b6ef7;
  font-weight: 600;
}

.cron-seg i {
  font-style: normal;
  font-size: 10px;
  color: #8e8e93;
}

.cron-hint {
  font-size: 11px;
  color: #8e8e93;
  margin-top: 6px;
  line-height: 1.4;
}

.cron-preview {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #eee;
}

.cron-preview-label {
  font-size: 11px;
  color: #8e8e93;
  margin-bottom: 4px;
}

.cron-time {
  font-family: monospace;
  font-size: 12px;
  color: #374151;
  line-height: 1.7;
}

.cron-error {
  font-size: 12px;
  color: #dc2626;
  line-height: 1.5;
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

.er-field-warning {
  font-size: 12px;
  color: #dc2626;
  line-height: 1.4;
  margin-top: 4px;
}

.llm-disabled-tag {
  margin-left: 6px;
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
