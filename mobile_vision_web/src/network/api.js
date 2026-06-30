/*
 * @Descripttion: 接口统一管理文件
 * @version:
 * @Author: wangbaojun
 * @Date: 2025-06-02 10:00:00
 */

import request from './axios';

export function register(params) {
  return request.post('/api/v1/user/register', params);
}

export function login(params) {
  return request.post('/api/v1/user/login', params);
}

export function getMyWorkspaces(params) {
  return request.post('/api/v1/workspace/my/list', params)
}

export function getMyUnWorkspaces(params) {
  return request.post('/api/v1/workspace/not-my/list', params)
}

export function getMyManageWorkspaces(params) {
  return request.post('/api/v1/workspace/my/manage/list', params)
}

export function createWorkspace(params) {
  return request.post('/api/v1/workspace/create', params)
}

export function updateWorkspace(params) {
  return request.put('/api/v1/workspace/update', params)
}

export function deleteWorkspace(params) {
  return request.delete('/api/v1/workspace/delete', params)
}

export function getWorkspaceDetail(params) {
  return request.get('/api/v1/workspace/detail', params)
}

export function getWorkspaceMemberDetail(params) {
  return request.get('/api/v1/workspace/member/detail', params)
}

export function getWorkspaceWithMembers(workspaceId) {
  return request.get(`/api/v1/workspace/detail-with-members/${workspaceId}`);
}

export function getWorkspaceMembers(params) {
  return request.get('/api/v1/workspace/member/list/', params);
}

export function addMemberByAdmin(params) {
  return request.post('/api/v1/workspace/member/add', params);
}

export function updateMemberRole(params) {
  return request.put('/api/v1/workspace/member/update', params);
}

export function removeMemberFromWorkspace(memberId) {
  return request.delete(`/api/v1/workspace/member/remove/${memberId}`);
}

export function joinWorkspace(params) {
  return request.post('/api/v1/workspace/member/join', params)
}

export function getRolesList() {
  return request.get('/api/v1/workspace/role/list')
}

export function getUserList(params) {
  return request.post('/api/v1/user/users/list', params)
}

export function getSystemConfigList(params) {
  return request.post('/api/v1/setting/system-config/list', params)
}

export function updateSystemConfig(params) {
  return request.put('/api/v1/setting/system-config/update', params)
}

export function updateSuperAdmin(params) {
  return request.post('/api/v1/user/super-admin/update', params);
}

export function getExtraAdminList() {
  return request.get('/api/v1/user/super-admin/list');
}

/* ==================== YOLO 相关接口 ==================== */

export function createYoloDataset(params) {
  const formData = new FormData();
  formData.append('name', params.name);
  formData.append('description', params.description || '');
  return request.post('/api/v1/dataset/create', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}

export function getYoloDatasets() {
  return request.get('/api/v1/dataset/list');
}

export function getYoloDataset(datasetId) {
  return request.get(`/api/v1/dataset/${datasetId}`);
}

export function deleteYoloDataset(datasetId) {
  return request.delete(`/api/v1/dataset/${datasetId}`);
}

export const updateYoloDataset = (datasetId, data) => {
  return request.post('/api/v1/dataset/update', {dataset_id: datasetId, ...data})
}

export const updateYoloDatasetClasses = (datasetId, classes) => {
  return request.post('/api/v1/dataset/update', {dataset_id: datasetId, classes})
}

export function uploadYoloImages(datasetId, files, split) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }
  formData.append('split', split);
  return request.post(`/api/v1/dataset/${datasetId}/images`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}

export function getDatasetImages(datasetId, split) {
  let url = `/api/v1/dataset/${datasetId}/images`;
  if (split) {
    url += `?split=${encodeURIComponent(split)}`;
  }
  return request.get(url);
}

export function getAnnotation(datasetId, imageName) {
  return request.get(`/api/v1/annotation/${datasetId}/${encodeURIComponent(imageName)}`);
}

export function saveAnnotation(datasetId, imageName, annotations) {
  return request.post(`/api/v1/annotation/${datasetId}/${encodeURIComponent(imageName)}`, annotations);
}

export function getTrainModels() {
  return request.get('/api/v1/train/models');
}

export function startTrain(params) {
  return request.post('/api/v1/train/start', params);
}

export function getTrainTasks(params = {}) {
  return request.get('/api/v1/train/tasks', params);
}

export function deleteTrainTask(taskId) {
  return request.delete(`/api/v1/train/tasks/${taskId}`);
}

export function abortTrainTask(taskId) {
  return request.post(`/api/v1/train/tasks/${taskId}/abort`);
}

export function retryTrainTask(taskId) {
  return request.post(`/api/v1/train/tasks/${taskId}/retry`);
}

export function deleteModel(modelId) {
  return request.delete(`/api/v1/model/${modelId}`);
}

export function predictImage(modelId, image, params = {}) {
  const formData = new FormData();
  formData.append('model_id', modelId);
  formData.append('image', image);
  if (params.conf_threshold !== undefined) {
    formData.append('conf_threshold', params.conf_threshold);
  }
  if (params.save_result !== undefined) {
    formData.append('save_result', params.save_result);
  }
  return request.post('/api/v1/model/predict', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}

export function getDeviceList() {
  return request.get('/api/v1/device/list');
}

export function refreshDevice(deviceId) {
  return request.post(`/api/v1/device/refresh/${deviceId}`);
}

/* ==================== LLM 凭证管理接口 ==================== */

export function createLLMCredential(params) {
  return request.post('/api/v1/llm/credential/create', params);
}

export function getLLMCredentialList(params) {
  const {page_num = 1, page_size = 100, ...otherParams} = params;
  return request.get('/api/v1/llm/credential/list', {page_num, page_size, ...otherParams});
}

export function getLLMCredentialWithKey(id) {
  return request.get('/api/v1/llm/credential/detail-with-key', {id});
}

export function updateLLMCredential(params) {
  return request.put('/api/v1/llm/credential/update', params);
}

export function deleteLLMCredential(id) {
  return request.delete('/api/v1/llm/credential/delete', {params: {id}});
}

/* ==================== 用例管理接口 ==================== */

export function createTestCase(params) {
  return request.post('/api/v1/testcase/create', params);
}

export function getTestCaseList(params) {
  return request.get('/api/v1/testcase/list', params);
}

export function getTestCaseDetail(id) {
  return request.get('/api/v1/testcase/detail', {case_id: id});
}

export function updateTestCase(params) {
  return request.put('/api/v1/testcase/update', params);
}

export function deleteTestCase(id) {
  return request.delete('/api/v1/testcase/delete', {params: {case_id: id}});
}


/* ==================== 测试任务接口 ==================== */

export function abortTestTask(taskId) {
  return request.post(`/api/v1/testtask/${taskId}/abort`);
}

export function deleteTestTask(taskId) {
  return request.delete(`/api/v1/testtask/delete`, { params: { task_id: taskId } });
}

export function abortTestJob(jobId) {
  return request.post(`/api/v1/testtask/job/${jobId}/abort`);
}

export function getModelsList(params = {}) {
  const {page = 1, page_size = 20, ...otherParams} = params;
  return request.get('/api/v1/model/list', {page, page_size, ...otherParams});
}

/* ==================== 测试计划接口 ==================== */

export function getTestPlanList(params) {
  return request.get('/api/v1/testplan/list', params);
}

export function getTestPlanDetail(planId) {
  return request.get(`/api/v1/testplan/${planId}`);
}

export function createTestPlan(params) {
  return request.post('/api/v1/testplan/create', params);
}

export function updateTestPlan(params) {
  return request.post('/api/v1/testplan/update', params);
}

export function deleteTestPlan(params) {
  return request.post('/api/v1/testplan/delete', params);
}

export function executeTestPlan(params) {
  return request.post('/api/v1/testplan/execute', params);
}

export function addCaseToPlan(params) {
  return request.post('/api/v1/testplan/add_case', params);
}

export function updateCaseRelation(params) {
  return request.post('/api/v1/testplan/update_case', params);
}

export function removeCaseRelation(params) {
  return request.post('/api/v1/testplan/remove_case', params);
}
