import { Reducer } from 'redux'; 
// 导入应用状态类型、操作类型集合及具体操作类型常量
import { AppState, AppActionTypes, SELECT_NODULE, SET_IMAGE, SET_NODULES, SET_WL, SET_WW } from './types';

/**
 * 应用的初始状态
 */
const initialState: AppState = {
  uploadedImage: null,       
  ww: 1500,                  
  wl: -600,                  
  nodules: [],                
  selectedNodule: null,      
};

const rootReducer: Reducer<AppState, AppActionTypes> = (state = initialState, action): AppState => {
  switch (action.type) {
    // 处理"设置上传图像"操作
    case SET_IMAGE:
      return { ...state, uploadedImage: action.payload };

    // 处理"设置窗宽"操作
    case SET_WW:
      return { ...state, ww: action.payload };

    // 处理"设置窗位"操作
    case SET_WL:
      return { ...state, wl: action.payload };

    // 处理"设置病灶列表"操作
    case SET_NODULES:
      return { ...state, nodules: action.payload };

    // 处理"选择病灶"操作
    case SELECT_NODULE:
      return { ...state, selectedNodule: action.payload };

    // 未匹配到任何操作类型时（默认情况）
    default:
      return state;
  }
};

export default rootReducer;