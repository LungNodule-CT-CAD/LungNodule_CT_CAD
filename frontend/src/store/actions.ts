// src/store/actions.ts

// 导入依赖模块和类型定义
import axios from 'axios';                     // 用于发起HTTP请求的库
import { Dispatch } from 'redux';              // Redux的Dispatch类型（用于分发action）
import { ThunkAction } from 'redux-thunk';      // Redux Thunk的异步action类型
import {                        // 导入应用状态类型、操作类型及常量
  AppActionTypes,
  AppState,
  Nodule,
  ImageFile,
  ADD_IMAGES,
  SET_ACTIVE_IMAGE,
  SET_NODULES_FOR_IMAGE,
  SELECT_NODULE,
  SET_SHOW_NODULES,
  SET_WW,
  SET_WL,
  SET_DETECT_STATUS,
  DetectStatus
} from './types';
import cornerstoneWADOImageLoader from 'cornerstone-wado-image-loader';
import dicomParser from 'dicom-parser';

/**
 * 上传多个图像文件的Thunk Action
 * @param files - 用户选择的File对象数组
 */
export const uploadImages =
  (files: File[]): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<AppActionTypes>) => {
    const imageFiles: ImageFile[] = await Promise.all(files.map(async file => {
      const isDicom = file.type === 'application/dicom' || file.name.toLowerCase().endsWith('.dcm');
      let imageUrl;
      let patientId = undefined;

      if (isDicom) {
        imageUrl = cornerstoneWADOImageLoader.wadouri.fileManager.add(file);
        // 解析DICOM PatientID
        try {
          const arrayBuffer = await file.arrayBuffer();
          const dataSet = dicomParser.parseDicom(new Uint8Array(arrayBuffer));
          patientId = dataSet.string('x00100020') || undefined;
        } catch (e) {
          patientId = undefined;
        }
      } else {
        imageUrl = URL.createObjectURL(file);
      }

      const imageFile: ImageFile = {
        id: `${new Date().getTime()}-${file.name}`,
        file: file,
        imageUrl: imageUrl,
        nodules: [],
        isDicom: isDicom,
        patientId: patientId,
      };
      return imageFile;
    }));

    if (imageFiles.length > 0) {
      dispatch({ type: ADD_IMAGES, payload: imageFiles });
    }
  };

/**
 * 设置当前活动图像的Action
 * @param imageId - 要设为活动的图像ID
 */
export const setActiveImage = (imageId: string | null): AppActionTypes => ({
  type: SET_ACTIVE_IMAGE,
  payload: imageId,
});

/**
 * 检测图像中病灶的异步action（Thunk）
 * 调用后端AI检测接口，获取病灶坐标并更新状态
 */
export const detectNodules =
  (): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<any>, getState: () => AppState) => {
    const { images, activeImageId } = getState();
    const activeImage = images.find(img => img.id === activeImageId);

    if (activeImage) {
      try {
        dispatch(setDetectStatus('detecting'));
        const formData = new FormData();
        formData.append('file', activeImage.file);

        console.log(`开始检测结节 for image: ${activeImage.id}`);
        const response = await axios.post('/api/predict', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const nodules = response.data.nodules;
        dispatch({
          type: SET_NODULES_FOR_IMAGE,
          payload: { imageId: activeImage.id, nodules },
        });
        dispatch(setShowNodules(true));
        if (nodules && nodules.length > 0) {
          dispatch(setDetectStatus('detected'));
        } else {
          dispatch(setDetectStatus('not_found'));
        }
        console.log('结节检测完成，已更新状态。');
      } catch (error) {
        dispatch(setDetectStatus('not_found'));
        console.error('检测病灶失败:', error);
      }
    } else {
      dispatch(setDetectStatus('not_started'));
      console.warn('请先上传并选择一张图片再进行检测。');
    }
  };

/**
 * 调整窗宽窗位的异步action（Thunk）
 * 注意：此功能在多图模式下可能需要调整，当前会影响全局WW/WL
 */
export const adjustWindow =
  (ww: number, wl: number): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<any>, getState: () => AppState) => {
      // 在多图模式下，调整窗宽窗位可能需要更复杂的逻辑
      // 例如，是调整所有图片还是仅活动图片？后端API是否支持？
      // 这里暂时只更新全局状态，具体实现可能需要根据产品需求调整
      dispatch({ type: SET_WW, payload: ww });
      dispatch({ type: SET_WL, payload: wl });
  };

/**
 * 选择病灶的同步action创建函数
 */
export const selectNodule = (nodule: Nodule | null): AppActionTypes => ({
  type: SELECT_NODULE,
  payload: nodule,
});

/**
 * 控制结节标注显示的同步action
 */
export const setShowNodules = (show: boolean): AppActionTypes => ({
  type: SET_SHOW_NODULES,
  payload: show,
});

export const setDetectStatus = (status: DetectStatus): AppActionTypes => ({
  type: SET_DETECT_STATUS,
  payload: status,
});