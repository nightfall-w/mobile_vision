/*
 * @Descripttion: Vue3 Axios 封装版本
 * @version:
 * @Author: baojun.wang
 */
import axios from 'axios';

// 注意：在axios拦截器中不能直接使用useRouter，需要在具体使用时处理
// 这里我们使用一个变量来存储router实例
let routerInstance = null;

// 设置router实例的方法
export const setRouter = (router) => {
  routerInstance = router;
};

// 创建 axios 实例
const service = axios.create({
  baseURL: import.meta.env.VITE_APP_SERVER_URL,
  timeout: 10000,
});

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // 添加 token 到请求头
    const currentUserSource = localStorage.getItem('currentUser');
    if (currentUserSource) {
      const currentUser = JSON.parse(currentUserSource);
      if (currentUser.access_token && currentUser.token_type) {
        config.headers.Authorization = currentUser.token_type + ' ' + currentUser.access_token;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    // 检查响应头中是否有新的 token
    const newToken = response.headers['new_token'];
    if (newToken) {
      // 更新本地存储的 token
      const currentUserSource = localStorage.getItem('currentUser');
      if (currentUserSource) {
        const currentUser = JSON.parse(currentUserSource);
        currentUser.access_token = newToken;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
      }
    }
    
    // 如果是 blob 或 arraybuffer 类型的响应，直接返回 response 对象，让调用方自己处理
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response;
    }
    
    return response.data; // 直接返回数据
  },
  (error) => {
    if (error?.response) {
      switch (error.response.status) {
        case 400:
          error.message = '请求错误';
          break;
        case 401:
          // 未认证，清除用户信息并重定向到登录页
          console.log('未认证的访问');
          localStorage.removeItem('currentUser');
          // 保存当前路径以便登录后重定向
          if (routerInstance) {
            const currentPath = routerInstance.currentRoute.value.fullPath;
            if (currentPath !== '/login') {
              localStorage.setItem('redirectPath', currentPath);
            }
            // 重定向到登录页
            routerInstance.push('/login');
          }
          error.message = '登录状态失效，请重新登录';
          break;
        case 403:
          // 无权限，不重定向到登录页，让具体页面处理
          console.log('无权限访问');
          error.message = '无权限访问';
          // 不清除用户信息，也不重定向
          break;
        default:
          error.message = `连接服务器失败: ${error.response.status}`;
      }
    } else {
      error.message = '网络异常或服务器无响应';
    }

    return Promise.reject(error);
  }
);

// 统一导出 GET、POST 方法（可选）
export default {
  get(url, params = {}, config = {}) {
    if (Object.keys(params).length > 0) {
      return service.get(url, {...config, params});
    }
    return service.get(url, config);
  },
  post(url, data = {}, config = {}) {
    return service.post(url, data, config);
  },
  put(url, data = {}, config = {}) {
    return service.put(url, data, config);
  },
  delete(url, params = {}, config = {}) {
    // 如果params已经是 axios 格式 {params: {...}}，直接传递
    if (params.params !== undefined) {
      return service.delete(url, {...config, ...params});
    }
    // 否则将 params 作为查询参数传递
    if (Object.keys(params).length > 0) {
      return service.delete(url, {...config, params: params});
    }
    return service.delete(url, config);
  }
};
