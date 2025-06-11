// src/store/actions.ts

// 导入依赖模块和类型定义
import axios from 'axios';                     // 用于发起HTTP请求的库
import { Dispatch } from 'redux';              // Redux的Dispatch类型（用于分发action）
import { ThunkAction } from 'redux-thunk';      // Redux Thunk的异步action类型
import {                        // 导入应用状态类型、操作类型及常量
  AppActionTypes,
  AppState,
  Nodule,
  SELECT_NODULE,
  SET_IMAGE,
  SET_NODULES,
  SET_WW,
  SET_WL
} from './types';

 
/**
 * 上传图像的异步action（Thunk）
 * 处理文件上传逻辑，并根据API响应更新应用状态
 * @param file - 用户选择的待上传图像文件（File对象）
 * @returns ThunkAction - 可异步执行的Redux action
 */
export const uploadImage =
  (file: File): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<AppActionTypes>) => {
    try {
      // 创建FormData对象，用于文件上传
      const formData = new FormData();
      formData.append('file', file);  // 将文件添加到formData中（键名'file'需与后端接口匹配）

      // 调用后端上传接口（假设接口地址为/api/upload）
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',  // 文件上传需指定此Content-Type
        },
      });

      // 上传成功：分发SET_IMAGE action，将服务器返回的图像路径存入状态
      // 假设后端返回格式：{ image: "base64字符串或图片URL" }
      dispatch({ type: SET_IMAGE, payload: response.data.image });
    } catch (error) {
      // 上传失败：打印错误日志（可扩展为分发错误提示action）
      console.error('上传图像失败:', error);
    }
  };


/**
 * 调整窗宽窗位的异步action（Thunk）
 * 调用后端接口调整图像显示参数，并更新应用状态
 * @param ww - 新的窗宽值（Window Width）
 * @param wl - 新的窗位值（Window Level）
 * @returns ThunkAction - 可异步执行的Redux action
 */
export const adjustWindow =
  (ww: number, wl: number): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<any>, getState: () => AppState) => {
    // 获取当前状态中的已上传图像路径（用于判断是否已上传图像）
    const { uploadedImage } = getState();

    // 仅当已上传图像时执行调整操作
    if (uploadedImage) {
      try {
        // 调用后端调整窗宽窗位接口（假设接口地址为/api/adjust-window）
        // 请求体包含当前窗宽、窗位和图像路径
        const response = await axios.post('/api/adjust-window', { ww, wl, image: uploadedImage });

        // 调整成功：
        // 1. 分发SET_IMAGE action，更新为调整后的图像（后端可能返回处理后的新图像）
        // 2. 分发SET_WW action，更新状态中的窗宽值
        // 3. 分发SET_WL action，更新状态中的窗位值
        dispatch({ type: SET_IMAGE, payload: response.data.image });
        dispatch({ type: SET_WW, payload: ww });
        dispatch({ type: SET_WL, payload: wl });
      } catch (error) {
        // 调整失败：打印错误日志
        console.error('调整窗宽窗位失败:', error);
      }
    }
  };


/**
 * 检测图像中病灶的异步action（Thunk）
 * 调用后端AI检测接口，获取病灶坐标并更新状态
 * @returns ThunkAction - 可异步执行的Redux action
 */
export const detectNodules =
  (): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<any>, getState: () => AppState) => {
    // 获取当前状态中的已上传图像路径
    const { uploadedImage } = getState();

    // 仅当已上传图像时执行检测操作
    if (uploadedImage) {
      try {
        // --- 真实后端API调用 ---
        console.log('开始检测结节...');
        
        // 调用后端病灶检测接口（接口地址为/api/detect-nodules）
        const response = await axios.post('/api/detect-nodules', { image: uploadedImage });

        // 检测成功：分发SET_NODULES action，将检测到的病灶列表存入状态
        dispatch({ type: SET_NODULES, payload: response.data.nodules });
        console.log('结节检测完成，已更新状态。');
      } catch (error) {
        // 检测失败：打印错误日志
        console.error('检测病灶失败:', error);
      }
    } else {
      console.warn('请先上传图像再进行检测。');
    }
  };


/**
 * 选择病灶的同步action创建函数
 * 用于标记当前选中的病灶（或取消选择）
 * @param nodule - 选中的病灶对象（或null表示取消选择）
 * @returns AppActionTypes - 包含SELECT_NODULE类型的action对象
 */
export const selectNodule = (nodule: Nodule | null): AppActionTypes => ({
  type: SELECT_NODULE,  // 操作类型：选择病灶
  payload: nodule,      // 负载数据：选中的病灶（或null）
});