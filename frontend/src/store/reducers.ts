import { Reducer } from 'redux'; 
// 导入应用状态类型、操作类型集合及具体操作类型常量
import { AppState, AppActionTypes, SELECT_NODULE, SET_WL, SET_WW, ADD_IMAGES, SET_ACTIVE_IMAGE, SET_NODULES_FOR_IMAGE, SET_SHOW_NODULES, SET_DETECT_STATUS } from './types';

/**
 * 应用的初始状态
 */
const initialState: AppState = {
  images: [],
  activeImageId: null,
  ww: 1500,                  
  wl: -600,                  
  selectedNodule: null,      
  showNodules: false,        // 初始不显示结节标注
  detectStatus: 'not_started', // 新增，初始为未检测
};

const rootReducer: Reducer<AppState, AppActionTypes> = (state = initialState, action): AppState => {
  switch (action.type) {
    case ADD_IMAGES:
      // 如果当前没有活动图片，则将第一张上传的图片设为活动图片
      const newActiveId = state.activeImageId ?? (action.payload.length > 0 ? action.payload[0].id : null);
      return {
        ...state,
        images: [...state.images, ...action.payload],
        activeImageId: newActiveId,
        detectStatus: 'not_started', // 新增，上传新图片时重置检测状态
      };

    case SET_ACTIVE_IMAGE:
      return { ...state, activeImageId: action.payload, selectedNodule: null, detectStatus: 'not_started' }; // 切换图片时重置检测状态

    // 处理"设置窗宽"操作
    case SET_WW:
      return { ...state, ww: action.payload };

    // 处理"设置窗位"操作
    case SET_WL:
      return { ...state, wl: action.payload };

    case SET_NODULES_FOR_IMAGE:
      return {
        ...state,
        images: state.images.map(image =>
          image.id === action.payload.imageId
            ? { ...image, nodules: action.payload.nodules }
            : image
        ),
      };

    // 处理"选择病灶"操作
    case SELECT_NODULE:
      return { ...state, selectedNodule: action.payload };

    // 处理"显示/隐藏结节标注"操作
    case SET_SHOW_NODULES:
      return { ...state, showNodules: action.payload };

    case SET_DETECT_STATUS:
      return { ...state, detectStatus: action.payload };

    // 未匹配到任何操作类型时（默认情况）
    default:
      return state;
  }
};

export default rootReducer;