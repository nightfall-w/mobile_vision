<template>
  <div class="app-container bg-gray-50 flex flex-col text-sm h-full">
    <!-- 固定区域：标题卡片 -->
    <div class="sticky-header">
      <!-- 页面标题卡片 -->
      <el-card class="header-card rounded-xl shadow-md border-0 overflow-hidden bg-white">
          <div class="relative overflow-hidden">
            <div class="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-blue-100 to-purple-100 rounded-full -mr-24 -mt-24 opacity-70"></div>
            <div class="absolute bottom-0 left-0 w-36 h-36 bg-gradient-to-tr from-green-100 to-blue-100 rounded-full -ml-18 -mb-18 opacity-70"></div>

            <div class="relative flex flex-col md:flex-row justify-between items-start md:items-center p-4 z-10">
              <div class="page-header mb-3 md:mb-0">
                <h1 class="text-xl font-bold text-gray-800 mb-1">工作空间</h1>
                <p class="text-sm text-gray-600">管理您的项目协作空间</p>
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
                  创建工作空间
                </el-button>
                <el-button
                  @click="showJoinDialog = true"
                  class="text-sm px-4"
                >
                  <el-icon class="mr-1" :size="14">
                    <UserFilled/>
                  </el-icon>
                  加入工作空间
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
        <!-- 标签页 -->
        <el-tabs v-model="activeTab" class="workspace-tabs px-4" @tab-change="handleTabChange">
          <el-tab-pane label="我管理的工作空间" name="managed">
            <div class="workspace-grid" v-loading="loading">
              <el-row :gutter="12">
                <!-- 工作空间卡片 -->
                <el-col
                  v-for="(workspace, index) in workspaces"
                  :key="workspace.workspace_id"
                  :span="24"
                  :sm="12"
                  :md="8"
                  :lg="6"
                  :xl="4"
                  class="mb-3"
                >
                  <div
                    class="workspace-card group bg-white rounded-lg shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden border border-gray-100 cursor-pointer relative"
                    @click="enterWorkspace(workspace)"
                  >
                    <!-- 操作图标（仅在管理的工作空间中显示） -->
                    <div
                      v-if="activeTab === 'managed'"
                      class="absolute top-2 right-2 flex gap-1 z-10"
                    >
                      <!-- 编辑图标 -->
                      <div
                        class="p-1 rounded-full bg-white bg-opacity-80 hover:bg-opacity-100 hover:bg-blue-50 cursor-pointer transition-all"
                        @click.stop="openEditDialog(workspace)"
                      >
                        <el-icon :size="14" class="text-gray-600 hover:text-blue-600">
                          <Edit/>
                        </el-icon>
                      </div>

                      <!-- 删除图标 -->
                      <div
                        class="p-1 rounded-full bg-white bg-opacity-80 hover:bg-opacity-100 hover:bg-red-50 cursor-pointer transition-all"
                        @click.stop="confirmDelete(workspace)"
                      >
                        <el-icon :size="14" class="text-gray-600 hover:text-red-600">
                          <Delete/>
                        </el-icon>
                      </div>
                    </div>

                    <div class="p-4">
                      <!-- 卡片头部 - 多彩图标 -->
                      <div class="flex items-center mb-2">
                        <div
                          class="w-6 h-6 rounded-lg flex items-center justify-center text-white font-bold text-[10px]"
                          :style="{ backgroundColor: getCardColor(workspace, index) }"
                        >
                          {{ getFirstLetter(workspace.workspace_name) }}
                        </div>
                        <h3 class="ml-2 font-semibold text-gray-800 text-xs truncate">
                          {{ workspace.workspace_name }}</h3>
                      </div>

                      <!-- 描述 -->
                      <p class="text-gray-500 text-xs mb-2 line-clamp-2 h-7">
                        {{ workspace.workspace_desc || '无描述信息' }}
                      </p>

                      <!-- 元数据 -->
                      <div class="text-gray-400 mb-2 flex items-center">
                        <el-icon :size="12" class="mr-1">
                          <Calendar/>
                        </el-icon>
                        <span class="text-[9px]">创建于 {{
                            formatTime(workspace.create_time)
                          }}</span>
                      </div>

                      <!-- 管理员 -->
                      <div class="mb-1 flex items-center flex-wrap">
                        <span class="text-[9px] text-gray-500 mr-1 whitespace-nowrap">管理员：</span>
                        <div class="flex flex-wrap gap-1">
                          <el-tag
                            v-for="manager in workspace.manager"
                            :key="manager.username || manager"
                            size="small"
                            effect="light"
                            class="bg-blue-50 text-blue-600 border-blue-100 text-[9px] px-1.5 py-0.5"
                          >
                            {{ manager.nickname || manager.username || manager }}
                          </el-tag>
                        </div>
                      </div>
                    </div>
                  </div>
                </el-col>

                <!-- 空状态 -->
                <el-col :span="24" v-if="workspaces.length === 0 && !loading">
                  <div
                    class="empty-state bg-white rounded-xl p-5 text-center border border-gray-100 mt-2">
                    <el-icon :size="48" class="text-gray-300 mb-2">
                      <OfficeBuilding/>
                    </el-icon>
                    <h3 class="text-gray-700 font-medium mb-1 text-sm">暂无工作空间</h3>
                    <p class="text-gray-500 mb-3 text-xs">创建一个工作空间开始协作吧</p>
                    <el-button
                      type="primary"
                      @click="openCreateDialog"
                      class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1.5"
                    >
                      创建工作空间
                    </el-button>
                  </div>
                </el-col>
              </el-row>
            </div>
          </el-tab-pane>

          <el-tab-pane label="我加入的工作空间" name="joined">
            <div class="workspace-grid" v-loading="loading">
              <el-row :gutter="12">
                <!-- 工作空间卡片 -->
                <el-col
                  v-for="(workspace, index) in workspaces"
                  :key="workspace.workspace_id"
                  :span="24"
                  :sm="12"
                  :md="8"
                  :lg="6"
                  :xl="4"
                  class="mb-3"
                >
                  <div
                    class="workspace-card group bg-white rounded-lg shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden border border-gray-100 cursor-pointer"
                    @click="enterWorkspace(workspace)"
                  >
                    <div class="p-4">
                      <!-- 卡片头部 - 多彩图标 -->
                      <div class="flex items-center mb-2">
                        <div
                          class="w-6 h-6 rounded-lg flex items-center justify-center text-white font-bold text-[10px]"
                          :style="{ backgroundColor: getCardColor(workspace, index) }"
                        >
                          {{ getFirstLetter(workspace.workspace_name) }}
                        </div>
                        <h3 class="ml-2 font-semibold text-gray-800 text-xs truncate">
                          {{ workspace.workspace_name }}</h3>
                      </div>

                      <!-- 描述 -->
                      <p class="text-gray-500 text-xs mb-2 line-clamp-2 h-7">
                        {{ workspace.workspace_desc || '无描述信息' }}
                      </p>

                      <!-- 元数据 -->
                      <div class="text-gray-400 mb-2 flex items-center">
                        <el-icon :size="12" class="mr-1">
                          <Calendar/>
                        </el-icon>
                        <span class="text-[9px]">创建于 {{
                            formatTime(workspace.create_time)
                          }}</span>
                      </div>

                      <!-- 管理员 -->
                      <div class="mb-1 flex items-center flex-wrap">
                        <span class="text-[9px] text-gray-500 mr-1 whitespace-nowrap">管理员：</span>
                        <div class="flex flex-wrap gap-1">
                          <el-tag
                            v-for="manager in workspace.manager"
                            :key="manager.username || manager"
                            size="small"
                            effect="light"
                            class="bg-blue-50 text-blue-600 border-blue-100 text-[9px] px-1.5 py-0.5"
                          >
                            {{ manager.nickname || manager.username || manager }}
                          </el-tag>
                        </div>
                      </div>
                    </div>
                  </div>
                </el-col>

                <!-- 空状态 -->
                <el-col :span="24" v-if="workspaces.length === 0 && !loading">
                  <div
                    class="empty-state bg-white rounded-xl p-5 text-center border border-gray-100 mt-2">
                    <el-icon :size="48" class="text-gray-300 mb-2">
                      <OfficeBuilding/>
                    </el-icon>
                    <h3 class="text-gray-700 font-medium mb-1 text-sm">暂无工作空间</h3>
                    <p class="text-gray-500 mb-3 text-xs">创建一个工作空间开始协作吧</p>
                    <el-button
                      type="primary"
                      @click="openCreateDialog"
                      class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1.5"
                    >
                      创建工作空间
                    </el-button>
                  </div>
                </el-col>
              </el-row>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 固定在底部的分页组件 -->
        <div class="table-footer" v-if="total > 0">
          <el-pagination
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
            :current-page="currentPage"
            :page-sizes="[12,24,48]"
            :page-size="pageSize"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            background
          />
        </div>
    </div>

    <!-- 创建工作空间对话框 -->
    <el-dialog v-model="showCreateDialog" width="520px" :close-on-click-modal="false" :before-close="handleCreateDialogClose" class="wc-dialog">
      <template #header>
        <div class="wc-header">
          <span class="wc-header-icon"><el-icon :size="20"><OfficeBuilding/></el-icon></span>
          <div>
            <h2 class="wc-header-title">创建工作空间</h2>
            <p class="wc-header-desc">创建一个新的工作空间并设置管理员</p>
          </div>
        </div>
      </template>
      <div class="wc-body">
        <div class="wc-section">
          <div class="wc-section-header">
            <span class="wc-section-icon"><el-icon><InfoFilled/></el-icon></span>
            <h3 class="wc-section-title">基本信息</h3>
          </div>
          <div class="wc-section-body">
            <div class="wc-field">
              <label class="wc-label">空间名称 <span class="wc-required">*</span></label>
              <el-input v-model="createForm.workspace_name" placeholder="请输入工作空间名称" clearable class="wc-input" />
            </div>
            <div class="wc-field">
              <label class="wc-label">空间描述</label>
              <el-input v-model="createForm.workspace_desc" type="textarea" :rows="3" placeholder="请输入工作空间描述（可选）" resize="none" class="wc-textarea" />
            </div>
          </div>
        </div>
        <div class="wc-section wc-section--amber">
          <div class="wc-section-header">
            <span class="wc-section-icon wc-section-icon--amber"><el-icon><Setting/></el-icon></span>
            <h3 class="wc-section-title">管理员设置</h3>
          </div>
          <div class="wc-section-body">
            <div class="wc-field">
              <label class="wc-label">选择管理员 <span class="wc-required">*</span></label>
              <el-select
                v-model="selectedManagers"
                multiple
                filterable
                remote
                lazy
                :remote-method="searchUsersForCreate"
                :loading="createSearchLoading"
                placeholder="请输入用户名或昵称搜索用户"
                value-key="username"
                class="wc-select"
              >
                <el-option
                  v-for="user in createUserSearchResults"
                  :key="user.username"
                  :label="`${user.nickname} (${user.username})`"
                  :value="user"
                />
              </el-select>
              <p class="wc-hint">最多可选择3个管理员</p>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="wc-footer">
          <el-button @click="showCreateDialog = false" class="wc-btn-cancel">取消</el-button>
          <el-button type="primary" @click="handleCreate" :loading="createLoading" class="wc-btn-primary">创建</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑工作空间对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑工作空间"
      width="450px"
      :before-close="handleEditDialogClose"
      class="custom-dialog"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="80px"
        class="space-y-4 py-2"
      >
        <el-form-item label="空间名称" prop="workspace_name" class="text-xs">
          <el-input
            v-model="editForm.workspace_name"
            placeholder="请输入工作空间名称"
            clearable
            class="rounded-md border-gray-200 text-xs"
          />
        </el-form-item>
        <el-form-item label="空间描述" prop="workspace_desc" class="text-xs">
          <el-input
            v-model="editForm.workspace_desc"
            type="textarea"
            :rows="3"
            placeholder="请输入工作空间描述（可选）"
            resize="none"
            class="rounded-md border-gray-200 text-xs"
          />
        </el-form-item>

        <!-- 管理员选择 -->
        <el-form-item label="管理员" prop="manager" class="text-xs">
          <el-select
            v-model="selectedEditManagers"
            multiple
            filterable
            remote
            lazy
            :remote-method="searchUsersForEdit"
            :loading="editSearchLoading"
            placeholder="请输入用户名或昵称搜索用户"
            class="w-full"
            :multiple-limit="3"
            value-key="username"
          >
            <el-option
              v-for="user in editUserSearchResults"
              :key="user.username"
              :label="`${user.nickname} (${user.username})`"
              :value="user"
            />
          </el-select>
          <div class="text-gray-500 text-xs mt-1">最多可选择3个管理员</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button
            @click="showEditDialog = false"
            class="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs py-1 px-2"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            @click="handleEdit"
            :loading="editLoading"
            class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1 px-2"
          >
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>


    <!-- 删除确认对话框 -->
    <el-dialog
      v-model="showDeleteDialog"
      title="删除确认"
      width="400px"
      :before-close="handleDeleteDialogClose"
      class="delete-dialog"
    >
      <div class="text-center py-6">
        <el-icon :size="48" class="text-red-500 mb-4">
          <Warning/>
        </el-icon>
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除工作空间吗？</h3>
        <p class="text-gray-600 mb-2">工作空间名称：<em><strong>{{
            deleteWorkspaceInfo.workspace_name
          }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">此操作不可撤销，请谨慎操作</p>

        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-left">
          <p class="text-yellow-700 text-xs flex items-start">
            <el-icon :size="14" class="mr-2 mt-0.5 flex-shrink-0">
              <InfoFilled/>
            </el-icon>
            <span>删除后，该工作空间下的所有数据将被永久删除，无法恢复</span>
          </p>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button
            @click="showDeleteDialog = false"
            class="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs py-1 px-2"
          >
            取消
          </el-button>
          <el-button
            type="danger"
            :disabled="deleteCountdown > 0"
            @click="handleDelete"
            :loading="deleteLoading"
            class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-xs py-1 px-2"
          >
            {{ deleteCountdown > 0 ? `确认删除 (${deleteCountdown}s)` : '确认删除' }}
          </el-button>
        </div>
      </template>
    </el-dialog>


    <!-- 降级管理员对话框 -->
    <el-dialog
      v-model="showDowngradeDialog"
      title="降级管理员"
      width="600px"
      class="downgrade-dialog"
    >
      <el-form
        ref="downgradeFormRef"
        :model="downgradeForm"
        :rules="downgradeRules"
        class="space-y-6 py-2"
      >
        <div>
          <div class="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-5">
            <p class="text-blue-700 text-xs flex items-center">
              <el-icon :size="14" class="mr-2 flex-shrink-0">
                <InfoFilled/>
              </el-icon>
              <span>您正在将管理员 <span class="font-bold text-blue-600">{{
                  downgradeInfo.manager
                }}</span> 降级为其他角色</span>
            </p>
          </div>

          <!-- 角色选择 -->
          <el-form-item prop="role_id" class="mb-0">
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
              <div
                v-for="role in downgradeInfo.availableRoles"
                :key="role.role_id"
                class="border-2 border-gray-400 rounded-lg p-4 cursor-pointer transition-all hover:border-blue-500 hover:bg-blue-50 relative group flex items-center"
                :class="{ 'border-blue-600 bg-blue-100 shadow-sm': downgradeForm.role_id === role.role_id }"
                @click="downgradeForm.role_id = role.role_id"
              >
                <h4 class="font-medium text-gray-800 text-sm truncate">{{ role.role_name }}</h4>
                <div
                  class="absolute bottom-0 left-0 right-0 bg-gray-800 bg-opacity-90 text-white text-xs p-2 rounded-b-lg transform translate-y-full opacity-0 group-hover:opacity-100 transition-all duration-200">
                  <div class="line-clamp-2">{{ role.role_description }}</div>
                </div>
              </div>
            </div>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button
            @click="handleDowngradeCancel"
            class="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs py-1 px-2"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            @click="handleDowngradeConfirm"
            :loading="downgradeLoading"
            class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1 px-2"
          >
            确认降级
          </el-button>
        </div>
      </template>
    </el-dialog>


    <!-- 简化版：加入工作空间对话框（单页形式） -->
    <el-dialog
      v-model="showJoinDialog"
      title="加入工作空间"
      width="520px"
      :close-on-click-modal="false"
      @opened="onJoinDialogOpened"
      class="join-dialog"
    >
      <el-form
        ref="joinFormRef"
        :model="joinForm"
        :rules="joinRules"
        class="space-y-6 py-2"
      >
        <!-- 工作空间搜索和选择 -->
        <div>
          <div class="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-5">
            <p class="text-blue-700 text-xs flex items-center">
              <el-icon :size="14" class="mr-2">
                <InfoFilled/>
              </el-icon>
              输入工作空间名称搜索并选择您要加入的空间
            </p>
          </div>

          <!-- 搜索框 -->
          <el-form-item prop="workspaceId" class="mb-3">
            <el-input
              v-model="joinSearchQuery"
              placeholder="输入工作空间名称搜索..."
              clearable
              class="h-9"
              @input="handleSearchInput"
              @clear="handleSearchClear"
              @focus="handleSearchFocus"
            >
              <template #prefix>
                <el-icon class="text-gray-400" :size="16">
                  <Search/>
                </el-icon>
              </template>
              <template #suffix>
                <el-icon v-if="joinSearchLoading" class="is-loading" :size="14">
                  <Loading/>
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <!-- 搜索结果区域 -->
          <div class="search-results-wrapper mt-2">
            <div
              class="search-results border rounded-lg overflow-hidden transition-all"
              :class="{ 'shadow-sm': searchResults.length > 0 }"
            >
              <!-- 加载中 -->
              <div v-if="joinSearchLoading" class="p-5 text-center">
                <el-icon class="is-loading" :size="18">
                  <Loading/>
                </el-icon>
                <span class="text-xs text-gray-500">正在搜索工作空间...</span>
              </div>

              <!-- 无结果且未选择工作空间 -->
              <div
                v-else-if="joinSearchQuery.trim() && searchResults.length === 0 && !joinForm.workspaceId"
                class="p-6 text-center">
                <div
                  class="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-3">
                  <el-icon :size="20" class="text-gray-400">
                    <Search/>
                  </el-icon>
                </div>
                <p class="text-sm text-gray-500">未找到匹配的工作空间</p>
                <p class="text-xs text-gray-400 mt-1">请尝试其他关键词搜索</p>
              </div>

              <!-- 结果列表 -->
              <div v-else-if="searchResults.length > 0" class="max-h-60 overflow-y-auto">
                <div class="divide-y divide-gray-100">
                  <div
                    v-for="(item, index) in searchResults"
                    :key="item.workspace_id"
                    class="p-3 hover:bg-blue-50 cursor-pointer transition-colors group"
                    @click="selectWorkspace(item)"
                  >
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-3">
                        <span class="font-medium text-gray-800 text-sm truncate max-w-xs">
                          {{ item.workspace_name }}
                        </span>
                        <span class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                          ID: {{ item.workspace_id }}
                        </span>
                      </div>
                      <div class="flex items-center">
                        <span class="text-xs text-gray-500 mr-2">
                          管理员: {{ getManagerNames(item.manager) }}
                        </span>
                        <div
                          class="w-3 h-3 rounded-full bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 初始提示 -->
              <div v-else-if="!joinSearchQuery.trim() && !joinForm.workspaceId"
                   class="p-5 text-center text-gray-500 text-xs">
                请输入工作空间名称开始搜索
              </div>

              <!-- 已选择工作空间但无搜索结果时不显示任何内容 -->
              <div v-else></div>
            </div>
          </div>
        </div>


        <!-- 角色选择 -->
        <div v-if="joinForm.workspaceId">

          <!-- 已选工作空间信息 -->
          <div class="bg-gray-50 border border-gray-100 rounded-lg p-4 mb-5">
            <div class="flex items-center">
              <div class="text-xs text-gray-500">已选工作空间：</div>
              <div class="ml-2 flex-1">
                <div class="font-medium text-sm text-gray-800 truncate">
                  {{ selectedWorkspaceInfo.workspace_name || '-' }}
                </div>
              </div>
            </div>
          </div>
          <div class="bg-purple-50 border border-purple-100 rounded-lg p-4 mb-5">
            <p class="text-purple-700 text-xs flex items-center">
              <el-icon :size="14" class="mr-2">
                <InfoFilled/>
              </el-icon>
              选择您在工作空间中的角色，将影响您拥有的权限
            </p>
          </div>

          <!-- 角色选择 -->
          <el-form-item prop="roleId" class="mb-0">
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full">
              <div
                v-for="role in roles.filter(r => r.role_name !== '管理员')"
                :key="role.role_id"
                class="border-2 border-gray-400 rounded-lg p-4 cursor-pointer transition-all hover:border-blue-500 hover:bg-blue-50 relative group flex items-center"
                :class="{ 'border-blue-600 bg-blue-100 shadow-sm': joinForm.roleId === role.role_id }"
                @click="joinForm.roleId = role.role_id"
              >
                <h4 class="font-medium text-gray-800 text-sm truncate">{{ role.role_name }}</h4>
                <div
                  class="absolute bottom-0 left-0 right-0 bg-gray-800 bg-opacity-90 text-white text-xs p-2 rounded-b-lg transform translate-y-full opacity-0 group-hover:opacity-100 transition-all duration-200">
                  <div class="line-clamp-2">{{ role.role_description }}</div>
                </div>
              </div>
            </div>
          </el-form-item>

        </div>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button
            @click="handleJoinDialogClose"
            class="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs py-1 px-2"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            @click="handleJoin"
            :loading="joinLoading"
            :disabled="!joinForm.workspaceId || !joinForm.roleId"
            class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1 px-2"
          >
            确认加入
          </el-button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import {nextTick, onMounted, reactive, ref, watch} from 'vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {
  Calendar,
  InfoFilled,
  OfficeBuilding,
  Plus,
  Search,
  UserFilled,
  Loading,
  Edit,
  Delete,
  Warning,
  Setting
} from '@element-plus/icons-vue'
import {
  createWorkspace,
  getMyUnWorkspaces,
  getMyManageWorkspaces,
  getMyWorkspaces,
  getRolesList,
  joinWorkspace,
  getUserList,
  updateWorkspace,
  deleteWorkspace
} from '@/network/api.js'
import {useRouter} from 'vue-router'
import {debounce} from 'lodash'

// 路由实例
const router = useRouter()

// 数据状态
const workspaces = ref([]) // 当前tab显示的工作空间
const loading = ref(false)
const createLoading = ref(false)
const editLoading = ref(false)
const joinLoading = ref(false)
const deleteLoading = ref(false)
const downgradeLoading = ref(false)
const total = ref(0) // 总条数

// 分页相关
const currentPage = ref(1)
const pageSize = ref(12)

// tab相关
const activeTab = ref('managed') // 当前激活的tab

// 对话框状态
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const showJoinDialog = ref(false)
const showDowngradeDialog = ref(false)

// 删除确认相关
const deleteCountdown = ref(5)
let countdownInterval = null
const deleteWorkspaceInfo = ref({
  workspace_id: '',
  workspace_name: ''
})

// 降级操作相关
const downgradeInfo = reactive({
  manager: '',
  workspace_id: '',
  availableRoles: [],
  resolve: null,
  reject: null
})
const downgradeFormRef = ref()
const downgradeForm = reactive({
  role_id: ''
})

// 加入工作空间表单数据
const joinFormRef = ref()
const joinForm = reactive({
  workspaceId: '',
  roleId: ''
})

// 加入工作空间验证规则
const joinRules = {
  workspaceId: [
    {required: true, message: '请选择工作空间', trigger: 'change'}
  ],
  roleId: [
    {required: true, message: '请选择角色', trigger: 'change'}
  ]
}

// 降级表单验证规则
const downgradeRules = {
  role_id: [
    {required: true, message: '请选择角色', trigger: 'change'}
  ]
}

// 加入工作空间相关
const joinSearchQuery = ref('')
const joinSearchLoading = ref(false)
const searchResults = ref([])
const roles = ref([]) // 角色列表
const selectedWorkspaceInfo = ref({}) // 已选工作空间信息
const hasFetchedInitialData = ref(false) // 是否已获取初始数据

// 用户搜索相关 - 为创建和编辑对话框分别维护搜索状态
const createSearchLoading = ref(false)
const editSearchLoading = ref(false)
const createUserSearchResults = ref([])
const editUserSearchResults = ref([])
const selectedManagers = ref([])
const selectedEditManagers = ref([]) // 编辑对话框中的管理员选择

// 创建表单
const createForm = reactive({
  workspace_name: '',
  workspace_desc: '',
  manager: [] // 添加管理员字段
})

// 编辑表单
const editFormRef = ref()
const editForm = reactive({
  workspace_id: '',
  workspace_name: '',
  workspace_desc: '',
  manager: [] // 管理员字段
})

// 编辑表单验证规则
const editRules = {
  workspace_name: [
    {required: true, message: '请输入工作空间名称', trigger: 'blur'},
    {max: 50, message: '名称不能超过50个字符', trigger: 'blur'}
  ],
  manager: [
    {required: true, message: '请至少选择一个管理员', trigger: 'change'},
    {type: 'array', min: 1, message: '请至少选择一个管理员', trigger: 'change'}
  ]
}

// 多彩颜色方案
const cardColors = [
  '#4299e1', '#38b2ac', '#805ad5', '#ed64a6', '#ed8936',
  '#319795', '#6b46c1', '#d53f8c', '#dd6b20', '#4c51bf',
  '#e53e3e', '#10b981', '#f56565', '#f6ad55', '#48bb78'
]


// 获取当前用户信息
const getCurrentUser = () => {
  try {
    const currentUserStr = localStorage.getItem('currentUser');
    if (currentUserStr) {
      return JSON.parse(currentUserStr);
    }
    return null;
  } catch (error) {
    console.error('解析当前用户信息失败:', error);
    return null;
  }
};

// 获取卡片颜色
const getCardColor = (workspace, index) => {
  const idx = index !== undefined ? index : Math.abs(workspace.workspace_name?.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % cardColors.length;
  return cardColors[idx % cardColors.length]
}

// 获取角色列表
const fetchRoles = async () => {
  try {
    const res = await getRolesList()
    if (res.code === 0) {
      roles.value = res.data || []
    } else {
      ElMessage.error(res.message || '获取角色列表失败')
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

// 组件挂载时加载数据
onMounted(() => {
  fetchWorkspaces()
  fetchRoles()
})

// 获取工作空间列表
const fetchWorkspaces = async () => {
  loading.value = true
  try {
    let res;
    if (activeTab.value === 'managed') {
      // 获取我管理的工作空间
      res = await getMyManageWorkspaces({
        page_num: currentPage.value,
        page_size: pageSize.value
      })
    } else {
      // 获取我加入的工作空间
      res = await getMyWorkspaces({
        page_num: currentPage.value,
        page_size: pageSize.value
      })
    }

    if (res.code === 0) {
      workspaces.value = res.data.workspaces || []
      total.value = res.data.total || 0
    } else {
      ElMessage.error(res.message || '获取工作空间失败')
    }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

// tab切换处理
const handleTabChange = () => {
  // 重置分页
  currentPage.value = 1
  fetchWorkspaces()
}

// 分页事件处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchWorkspaces()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchWorkspaces()
}

// 辅助函数：获取首字母
const getFirstLetter = (name) => {
  if (!name) return 'W'
  return name.charAt(0).toUpperCase()
}

// 辅助函数：格式化时间
const formatTime = (timeString) => {
  if (!timeString) return '未知时间'
  const date = new Date(timeString)
  return date.toLocaleDateString()
}

// 辅助函数：获取管理员名称
const getManagerNames = (managers) => {
  if (!managers || !managers.length) return '无'
  return managers.map(m => m.nickname || m.username || m).join('，')
}

// 进入工作空间
const enterWorkspace = (workspace) => {
  router.push(`/workspace/${workspace.workspace_id}`)
}

// 搜索用户 - 创建对话框专用
const searchUsersForCreate = async (query) => {
  if (!query) {
    createUserSearchResults.value = []
    return
  }

  createSearchLoading.value = true
  try {
    const res = await getUserList({
      search: query,
      page_num: 1,
      page_size: 10
    })

    if (res.code === 0) {
      createUserSearchResults.value = res.data.list || []
    } else {
      ElMessage.error(res.message || '搜索用户失败')
      createUserSearchResults.value = []
    }
  } catch (error) {
    ElMessage.error('搜索用户失败')
    createUserSearchResults.value = []
  } finally {
    createSearchLoading.value = false
  }
}

// 搜索用户 - 编辑对话框专用
const searchUsersForEdit = async (query) => {
  if (!query) {
    editUserSearchResults.value = []
    return
  }

  editSearchLoading.value = true
  try {
    const res = await getUserList({
      search: query,
      page_num: 1,
      page_size: 10
    })

    if (res.code === 0) {
      editUserSearchResults.value = res.data.list || []
    } else {
      ElMessage.error(res.message || '搜索用户失败')
      editUserSearchResults.value = []
    }
  } catch (error) {
    ElMessage.error('搜索用户失败')
    editUserSearchResults.value = []
  } finally {
    editSearchLoading.value = false
  }
}

// 打开创建工作空间对话框
const openCreateDialog = async () => {
  // 1. 先清空所有状态
  createForm.workspace_name = ''
  createForm.workspace_desc = ''
  createForm.manager = []
  selectedManagers.value = []
  createUserSearchResults.value = []

  // 2. 打开弹窗
  showCreateDialog.value = true
  await nextTick()

  // 3. 延迟赋值（确保select渲染完成）
  setTimeout(() => {
    const currentUser = getCurrentUser()
    if (!currentUser) return

    const defaultManager = {
      username: currentUser.username,
      nickname: currentUser.nickname || currentUser.username
    }

    // 关键：同时给下拉选项和选中值赋值
    createUserSearchResults.value = [defaultManager]
    // 给v-model赋值，触发watch同步到createForm.manager
    selectedManagers.value = [defaultManager]
  }, 500)
}

// 创建工作空间
const handleCreate = async () => {
  if (!createForm.workspace_name.trim()) {
    ElMessage.warning('请输入工作空间名称')
    return
  }
  if (createForm.workspace_name.trim().length > 50) {
    ElMessage.warning('名称不能超过50个字符')
    return
  }
  if (!selectedManagers.value.length) {
    ElMessage.warning('请至少选择一个管理员')
    return
  }

  createLoading.value = true
  try {
    // 构造请求参数
    const requestData = {
      workspace_name: createForm.workspace_name,
      workspace_desc: createForm.workspace_desc,
      manager: createForm.manager
    }

    console.log('创建请求参数：', requestData);
    const res = await createWorkspace(requestData)
    if (res.code === 0) {
      ElMessage.success('创建成功')
      showCreateDialog.value = false
      // 重置表单
      createForm.workspace_name = ''
      createForm.workspace_desc = ''
      createForm.manager = []
      selectedManagers.value = []
      createUserSearchResults.value = []
      fetchWorkspaces()
    } else {
      ElMessage.error(res.message || '创建失败：接口返回错误')
    }
  } catch (error) {
    console.error('创建失败详情：', error);
    if (error.name !== 'ValidationError') {
      ElMessage.error('创建失败：网络或服务器错误')
    }
  } finally {
    createLoading.value = false
  }
}

// 打开编辑对话框
const openEditDialog = async (workspace) => {
  console.log('openEditDialog:', workspace);

  // 1. 先清空所有状态，避免残留数据导致渲染压力
  editForm.workspace_id = ''
  editForm.workspace_name = ''
  editForm.workspace_desc = ''
  editForm.manager = []
  selectedEditManagers.value = []
  editUserSearchResults.value = []

  // 2. 先填充基础表单数据（非select部分）
  editForm.workspace_id = workspace.workspace_id
  editForm.workspace_name = workspace.workspace_name
  editForm.workspace_desc = workspace.workspace_desc

  // 3. 先显示对话框，等待DOM完全渲染
  showEditDialog.value = true
  await nextTick()

  // 4. 延迟处理管理员数据（核心：避免select初始化时赋值）
  setTimeout(() => {
    // 处理管理员数据 - 支持多种格式
    if (workspace.manager && Array.isArray(workspace.manager) && workspace.manager.length > 0) {
      // 将 manager 转换为包含 username 和 nickname 的对象数组
      const managerObjects = workspace.manager.map(m => {
        // 如果是字符串，直接使用
        if (typeof m === 'string') {
          return { username: m, nickname: m }
        }
        // 如果是对象
        return {
          username: m.username || m,
          nickname: m.nickname || m.username || m
        }
      })

      // 先给搜索结果赋值（确保下拉选项能显示）
      editUserSearchResults.value = [...managerObjects];

      // 延迟赋值v-model（避免select校验循环）
      setTimeout(() => {
        selectedEditManagers.value = [...managerObjects];
        editForm.manager = managerObjects.map(m => m.username);
      }, 100);
    } else {
      editForm.manager = []
      selectedEditManagers.value = []
    }
  }, 300);
}

// 恢复watch并优化：实时同步selectedManagers到createForm.manager
watch(selectedManagers, (newVal) => {
  // 把选中的管理员对象数组转换为username字符串数组
  createForm.manager = newVal.map(m => m.username);
}, {immediate: true});

// 编辑对话框同理，同步selectedEditManagers到editForm.manager
watch(selectedEditManagers, (newVal) => {
  editForm.manager = newVal.map(m => m.username);
}, {immediate: true});

// 编辑工作空间
const handleEdit = async () => {
  if (!editFormRef.value) return

  try {
    await editFormRef.value.validate()
    editLoading.value = true

    // 确定被删除的管理员列表
    const currentManagers = editForm.manager;
    const originalManagers = workspaces.value
      .find(w => w.workspace_id === editForm.workspace_id)
      ?.manager.map(m => m.username || m) || [];

    // 找出被删除的管理员
    const removedManagers = originalManagers.filter(m => !currentManagers.includes(m));

    let deleteManagerInfoList = [];
    let removedManagerDetails = []; // 保存被移除管理员的详细信息用于确认

    // 如果有被删除的管理员，需要处理
    if (removedManagers.length > 0) {
      // 先保存编辑表单数据
      const editData = {
        workspace_id: editForm.workspace_id,
        workspace_name: editForm.workspace_name,
        workspace_desc: editForm.workspace_desc,
        manager: editForm.manager
      };

      // 处理每个被删除的管理员
      for (const managerUsername of removedManagers) {
        // 查找管理员详细信息
        const managerDetail = editUserSearchResults.value.find(u => u.username === managerUsername) ||
          workspaces.value
            .find(w => w.workspace_id === editForm.workspace_id)
            ?.manager.find(m => (m.username || m) === managerUsername) ||
          {username: managerUsername, nickname: managerUsername};

        try {
          // 弹出对话框让用户选择删除还是降级
          const action = await new Promise((resolve) => {
            ElMessageBox.confirm(
              `您要删除管理员 <strong class="text-blue-600">${managerDetail.nickname} (${managerDetail.username})</strong>，是要直接删除还是将其降级为其他角色？`,
              '操作确认',
              {
                distinguishCancelAndClose: true,
                confirmButtonText: '降级',
                cancelButtonText: '删除',
                dangerouslyUseHTMLString: true,
                type: 'warning'
              }
            ).then(() => {
              resolve('downgrade');
            }).catch(action => {
              if (action === 'cancel') {
                resolve('delete');
              } else {
                resolve('cancel');
              }
            });
          });

          if (action === 'cancel') {
            // 用户取消操作，中断整个编辑流程
            throw new Error('用户取消操作');
          } else if (action === 'downgrade') {
            // 用户选择降级，打开降级对话框
            const roleId = await openDowngradeDialog(`${managerDetail.nickname} (${managerDetail.username})`, editForm.workspace_id);
            deleteManagerInfoList.push({
              username: managerUsername,
              role_id: roleId
            });
            removedManagerDetails.push({
              username: managerUsername,
              nickname: managerDetail.nickname,
              action: '降级',
              roleId: roleId,
              roleName: roles.value.find(r => r.role_id === roleId)?.role_name || '未知角色'
            });
          } else {
            // 用户选择删除
            deleteManagerInfoList.push({
              username: managerUsername,
              role_id: null
            });
            removedManagerDetails.push({
              username: managerUsername,
              nickname: managerDetail.nickname,
              action: '删除'
            });
          }
        } catch (error) {
          // 用户取消操作，中断整个编辑流程
          throw new Error('用户取消操作');
        }
      }

      // 显示最终确认对话框
      const confirmText = removedManagerDetails.map(m =>
        `<div class="mb-2">
          <span class="font-medium">${m.nickname} (${m.username})</span>:
          <span class="${m.action === '删除' ? 'text-red-600' : 'text-blue-600'}">${m.action}</span>
          ${m.action === '降级' ? `为 ${m.roleName}` : ''}
        </div>`
      ).join('');

      await ElMessageBox.confirm(
        `<div class="py-2">
          <p class="mb-3">请确认以下管理员变更操作：</p>
          ${confirmText}
        </div>`,
        '最终确认',
        {
          dangerouslyUseHTMLString: true,
          confirmButtonText: '确认提交',
          cancelButtonText: '取消',
          type: 'warning'
        }
      );

      // 构造请求参数
      const requestData = {
        workspace_id: editData.workspace_id,
        workspace_name: editData.workspace_name,
        workspace_desc: editData.workspace_desc,
        manager: editData.manager,
        delete_manager_info_list: deleteManagerInfoList
      }

      const res = await updateWorkspace(requestData)
      if (res.code === 0) {
        ElMessage.success('更新成功')
        showEditDialog.value = false
        fetchWorkspaces()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
    } else {
      // 没有被删除的管理员，直接更新
      // 显示确认对话框
      await ElMessageBox.confirm(
        '确认保存对工作空间的修改吗？',
        '确认保存',
        {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'info'
        }
      );

      const requestData = {
        workspace_id: editForm.workspace_id,
        workspace_name: editForm.workspace_name,
        workspace_desc: editForm.workspace_desc,
        manager: editForm.manager
      }

      const res = await updateWorkspace(requestData)
      if (res.code === 0) {
        ElMessage.success('更新成功')
        showEditDialog.value = false
        fetchWorkspaces()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
    }
  } catch (error) {
    if (error.message !== '用户取消操作' && error?.code !== 'ERR_BAD_RESPONSE') {
      ElMessage.error('更新失败')
    }
  } finally {
    editLoading.value = false
  }
}

// 打开降级对话框
const openDowngradeDialog = (manager, workspace_id) => {
  return new Promise((resolve, reject) => {
    // 设置降级信息
    downgradeInfo.manager = manager;
    downgradeInfo.workspace_id = workspace_id;
    downgradeInfo.availableRoles = roles.value.filter(role => role.role_name !== '管理员');
    downgradeInfo.resolve = resolve;
    downgradeInfo.reject = reject;
    downgradeForm.role_id = '';

    // 显示降级对话框
    showDowngradeDialog.value = true;
  });
};

// 处理降级确认
const handleDowngradeConfirm = async () => {
  try {
    await downgradeFormRef.value.validate();
    showDowngradeDialog.value = false;
    downgradeInfo.resolve(downgradeForm.role_id);
  } catch (error) {
    ElMessage.error('请选择一个角色');
  }
};

// 处理降级取消
const handleDowngradeCancel = () => {
  showDowngradeDialog.value = false;
  downgradeInfo.reject(new Error('用户取消操作'));
};

// 关闭编辑对话框
const handleEditDialogClose = (done) => {
  ElMessageBox.confirm('确定要放弃编辑吗？已输入的内容将丢失')
    .then(() => {
      // 彻底清空所有相关状态
      editForm.workspace_id = ''
      editForm.workspace_name = ''
      editForm.workspace_desc = ''
      editForm.manager = []
      selectedEditManagers.value = []
      editUserSearchResults.value = []
      done()
    })
    .catch(() => {
    })
}

// 加入工作空间
const handleJoin = async () => {
  if (!joinFormRef.value) return

  try {
    await joinFormRef.value.validate()
    joinLoading.value = true

    const requestData = {
      workspace_id: joinForm.workspaceId,
      role_id: joinForm.roleId
    }

    const res = await joinWorkspace(requestData)
    if (res.code === 0) {
      ElMessage.success('加入成功')
      showJoinDialog.value = false
      // 重置表单
      joinForm.workspaceId = ''
      joinForm.roleId = ''
      selectedWorkspaceInfo.value = {}
      searchResults.value = []
      joinSearchQuery.value = ''
      fetchWorkspaces()
    } else {
      ElMessage.error(res.message || '加入失败')
    }
  } catch (error) {
    if (error.name !== 'ValidationError') {
      ElMessage.error('加入失败')
    }
  } finally {
    joinLoading.value = false
  }
}

// 确认删除工作空间
const confirmDelete = (workspace) => {
  // 设置要删除的工作空间信息
  deleteWorkspaceInfo.value.workspace_id = workspace.workspace_id
  deleteWorkspaceInfo.value.workspace_name = workspace.workspace_name

  // 显示删除确认对话框
  showDeleteDialog.value = true

  // 重置倒计时
  deleteCountdown.value = 5
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }

  // 开始倒计时
  countdownInterval = setInterval(() => {
    deleteCountdown.value--
    if (deleteCountdown.value <= 0) {
      clearInterval(countdownInterval)
    }
  }, 1000)
}

// 执行删除工作空间
const handleDelete = async () => {
  deleteLoading.value = true
  try {
    // 使用正确的参数格式调用deleteWorkspace
    const res = await deleteWorkspace({workspace_id: deleteWorkspaceInfo.value.workspace_id})
    if (res.code === 0) {
      ElMessage.success('删除成功')
      showDeleteDialog.value = false
      // 确保定时器被清除
      if (countdownInterval) {
        clearInterval(countdownInterval)
        countdownInterval = null
      }
      fetchWorkspaces()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    console.error('Delete error:', error)
    ElMessage.error('删除失败: ' + (error.message || '未知错误'))
  } finally {
    deleteLoading.value = false
    // 确保定时器被清除
    if (countdownInterval) {
      clearInterval(countdownInterval)
      countdownInterval = null
    }
  }
}

// 关闭删除确认对话框
const handleDeleteDialogClose = (done) => {
  showDeleteDialog.value = false
  // 确保定时器被清除
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
  done()
}

// 关闭创建对话框
const handleCreateDialogClose = (done) => {
  ElMessageBox.confirm('确定要放弃创建吗？已输入的内容将丢失')
    .then(() => {
      createForm.workspace_name = ''
      createForm.workspace_desc = ''
      createForm.manager = []
      selectedManagers.value = []
      createUserSearchResults.value = []
      done()
    })
    .catch(() => {
    })
}

// 搜索工作空间（加入工作空间用）
const searchWorkspaces = async (query) => {
  if (!query) {
    searchResults.value = []
    return
  }

  joinSearchLoading.value = true
  try {
    const res = await getMyUnWorkspaces({
      workspace_name: query,
      page_num: 1,
      page_size: 10
    })

    if (res.code === 0) {
      searchResults.value = res.data.workspaces || []
    } else {
      ElMessage.error(res.message || '搜索工作空间失败')
      searchResults.value = []
    }
  } catch (error) {
    ElMessage.error('搜索工作空间失败')
    searchResults.value = []
  } finally {
    joinSearchLoading.value = false
  }
}

// 防抖搜索
const debouncedSearch = debounce(searchWorkspaces, 300)

// 处理搜索输入
const handleSearchInput = (query) => {
  if (query) {
    debouncedSearch(query)
  } else {
    searchResults.value = []
  }
}

// 处理搜索清空
const handleSearchClear = () => {
  searchResults.value = []
  joinSearchQuery.value = ''
}

// 处理搜索聚焦
const handleSearchFocus = () => {
  if (joinSearchQuery.value) {
    debouncedSearch(joinSearchQuery.value)
  }
}

// 选择工作空间
const selectWorkspace = (workspace) => {
  joinForm.workspaceId = workspace.workspace_id
  selectedWorkspaceInfo.value = workspace
  searchResults.value = []

  // 手动触发表单验证，解决第一次选择后仍提示"请选择工作空间"的问题
  nextTick().then(() => {
    if (joinFormRef.value) {
      joinFormRef.value.validateField('workspaceId')
    }
  })
}

// 加入对话框打开时的处理
const onJoinDialogOpened = async () => {
  if (!hasFetchedInitialData.value) {
    await fetchRoles()
    hasFetchedInitialData.value = true
  }
}

// 关闭加入对话框
const handleJoinDialogClose = () => {
  showJoinDialog.value = false
  // 重置表单
  joinForm.workspaceId = ''
  joinForm.roleId = ''
  selectedWorkspaceInfo.value = {}
  searchResults.value = []
  joinSearchQuery.value = ''
}

// 选择角色
const selectRole = (role) => {
  joinForm.roleId = role.role_id
}
</script>


<style scoped>
/* 基础样式 */
.app-container {
  font-family: 'Inter', system-ui, sans-serif;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 固定头部区域 */
.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f5f5f5;
  padding-bottom: 16px;
}

/* 滚动内容区域 */
.scroll-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* 页面标题卡片样式 */
.header-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 12px;
}

/* 页面标题区域 */
.page-header {
  z-index: 10;
}

.page-header h1 {
  margin: 0;
}

.page-header p {
  margin: 4px 0 0;
}

/* 工作空间卡片 */
.workspace-card {
  transform: translateY(0);
  transition: all 0.2s ease;
}

.workspace-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

/* 空状态 */
.empty-state {
  margin-top: 1rem;
}

/* 固定底部的分页组件 */
.table-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px 20px;
  margin-top: 10px;
  background-color: white;
  border-top: 1px solid #ebeef5;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  z-index: 100;
}

/* ===== 创建工作空间弹窗 ===== */
.wc-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.wc-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.wc-dialog :deep(.el-dialog__footer) {
  padding: 0;
}

.wc-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 24px 24px 0;
}

.wc-header-icon {
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

.wc-header-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.wc-header-desc {
  margin: 2px 0 0;
  font-size: 13px;
  color: #8e8e93;
}

.wc-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.wc-section {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  border-left: 2px solid #4b8af4;
  overflow: hidden;
}

.wc-section--amber {
  border-left-color: #e8962e;
}

.wc-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f5f7fd;
  border-bottom: 1px solid #e5e7eb;
}

.wc-section--amber .wc-section-header {
  background: #fef8f0;
}

.wc-section-icon {
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

.wc-section-icon--amber {
  background: #fef3e8;
  color: #e8962e;
}

.wc-section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.wc-section-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wc-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.wc-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.wc-required {
  color: #dc2626;
}

.wc-hint {
  margin: 2px 0 0;
  font-size: 12px;
  color: #9ca3af;
}

.wc-input .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.wc-input .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.wc-input .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.wc-input .el-input__inner {
  height: 38px;
  font-size: 14px;
}

.wc-textarea .el-textarea__inner {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
  border: none;
  font-size: 14px;
  font-family: inherit;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.wc-textarea .el-textarea__inner:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.wc-textarea .el-textarea__inner:focus {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.wc-select {
  width: 100%;
}

.wc-select .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
}

.wc-select .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.wc-select .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.wc-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.wc-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 20px;
}

.wc-btn-primary {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 22px;
  background: #5b6ef7;
  border-color: #5b6ef7;
  box-shadow: 0 1px 3px rgba(91, 110, 247, 0.3);
  transition: all 0.15s ease;
}

.wc-btn-primary:hover {
  background: #4c5fd8;
  border-color: #4c5fd8;
  box-shadow: 0 2px 6px rgba(91, 110, 247, 0.4);
}

:deep(.el-dialog) {
  --el-dialog-border-radius: 12px;
  --el-dialog-padding-primary: 20px 24px;
  --el-dialog-title-font-size: 16px;
}

/* 搜索相关样式 */
.search-results-wrapper {
  transition: all 0.2s;
}

.search-results {
  border-color: #e5e7eb;
}

/* 角色卡片样式 */
:deep(.el-radio__input.is-checked .el-radio__inner) {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

/* 对话框按钮容器 */
:deep(.el-dialog__footer) {
  padding: 12px 24px !important;
  border-top: none !important;
}

/* 缩小按钮 */
:deep(.el-dialog__footer .el-button) {
  padding: 4px 8px !important;
  font-size: 12px !important;
}

/* 响应式调整 */
@media (max-width: 768px) {
  :deep(.el-dialog) {
    width: 92% !important;
  }
}

/* 下拉选项样式调整 */
:deep(.el-select-dropdown__item) {
  font-size: 11px;
  padding: 6px 10px;
}

/* 响应式布局调整 */
@media (min-width: 1920px) {
  :deep(.el-col-xl-4) {
    width: 20% !important;
  }
}

@media (max-width: 1919px) and (min-width: 1200px) {
  :deep(.el-col-lg-6) {
    width: 25% !important;
  }
}

@media (max-width: 1199px) and (min-width: 992px) {
  :deep(.el-col-md-8) {
    width: 33.3333% !important;
  }
}

@media (max-width: 991px) and (min-width: 768px) {
  :deep(.el-col-sm-12) {
    width: 50% !important;
  }
}

@media (max-width: 767px) {
  :deep(.el-col-24) {
    width: 100% !important;
  }
}

:deep(.el-form-item__content) {
  margin: 0;
  padding: 0;
}

/* 加载图标旋转动画 */
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 角色描述悬停效果 */
.role-description-tooltip {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 8px;
  border-radius: 0 0 8px 8px;
  transform: translateY(100%);
  opacity: 0;
  transition: opacity 0.2s ease;
  font-size: 12px;
  z-index: 10;
}

/* 标签页样式 */
:deep(.workspace-tabs) {
  display: flex;
  flex-direction: column;
  flex: 1;
}

:deep(.workspace-tabs .el-tabs__header) {
  margin-bottom: 20px;
  flex-shrink: 0;
}

:deep(.workspace-tabs .el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}

:deep(.workspace-tabs .el-tabs__nav-wrap::after) {
  height: 1px;
}

/* 降级对话框中的用户名高亮 */
.downgrade-dialog :deep(.el-message-box__message) strong {
  color: #3b82f6;
  font-weight: 600;
}
</style>
