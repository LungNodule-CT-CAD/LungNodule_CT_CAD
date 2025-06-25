// src/store/types.ts

/**
 * 定义图像中病灶区域的结构接口
 * 用于描述医学影像（如CT/MRI）中标记的病灶轮廓信息
 */
export interface Nodule {
    id: number;           // 病灶唯一标识ID（用于区分不同病灶）
    contour: Array<{ x: number; y: number; }>; // 组成病灶轮廓的点集
}

/**
 * 定义上传的图像文件的结构
 */
export interface ImageFile {
  id: string; // 使用时间戳和文件名生成的唯一ID
  file: File;
  imageUrl: string; // 对于DICOM，这是 Cornerstone 的 imageId；对于其他格式，是 Object URL
  nodules: Nodule[];
  isDicom: boolean; // 新增字段，标记是否为DICOM图像
  patientId?: string; // 新增，DICOM患者ID
}

/**
 * 定义应用的根状态结构
 * 包含应用运行时需要全局管理的所有核心数据
 */
export interface AppState {
  images: ImageFile[]; // 所有上传的图片
  activeImageId: string | null; // 当前活动图片的ID
  ww: number;                     // 窗宽（Window Width）- 用于控制图像对比度的参数
  wl: number;                     // 窗位（Window Level）- 用于控制图像亮度的参数
  selectedNodule: Nodule | null;  // 当前选中的病灶（null表示未选择任何病灶）
  showNodules: boolean;           // 是否显示结节标注
  detectStatus: DetectStatus; // 新增检测状态
}

// 定义所有可能的Action类型常量（用于标识状态操作类型）
export const ADD_IMAGES = 'ADD_IMAGES';        // 触发"添加图片"
export const SET_ACTIVE_IMAGE = 'SET_ACTIVE_IMAGE'; // 触发"设置活动图片"
export const SET_WW = 'SET_WW';            // 触发"设置窗宽"操作的标识
export const SET_WL = 'SET_WL';            // 触发"设置窗位"操作的标识
export const SET_NODULES_FOR_IMAGE = 'SET_NODULES_FOR_IMAGE';  // 触发"为指定图片设置结节"
export const SELECT_NODULE = 'SELECT_NODULE'; // 触发"选择病灶"操作的标识
export const SET_SHOW_NODULES = 'SET_SHOW_NODULES'; // 触发"显示/隐藏结节标注"操作的标识
export const SET_DETECT_STATUS = 'SET_DETECT_STATUS';

/**
 * 添加图像的Action接口
 */
interface AddImagesAction {
  type: typeof ADD_IMAGES;
  payload: ImageFile[];
}

/**
 * 设置活动图像的Action接口
 */
interface SetActiveImageAction {
  type: typeof SET_ACTIVE_IMAGE;
  payload: string | null;
}

/**
 * 设置窗宽的Action接口
 * 用于调整图像显示的对比度参数
 */
interface SetWwAction {
  type: typeof SET_WW;     // 操作类型（固定为SET_WW）
  payload: number;         // 携带的数据：新的窗宽数值（通常为正整数）
}

/**
 * 设置窗位的Action接口
 * 用于调整图像显示的亮度参数
 */
interface SetWlAction {
  type: typeof SET_WL;     // 操作类型（固定为SET_WL）
  payload: number;         // 携带的数据：新的窗位数值（通常与窗宽相关）
}

/**
 * 为指定图片设置结节列表的Action接口
 */
interface SetNodulesForImageAction {
  type: typeof SET_NODULES_FOR_IMAGE;
  payload: {
    imageId: string;
    nodules: Nodule[];
  };
}

/**
 * 选择病灶的Action接口
 * 用于标记当前用户选中的病灶区域
 */
interface SelectNoduleAction {
  type: typeof SELECT_NODULE;  // 操作类型（固定为SELECT_NODULE）
  payload: Nodule | null;      // 携带的数据：选中的病灶对象（或null表示取消选择）
}

/**
 * 设置显示/隐藏病灶的Action接口
 * 用于控制是否显示病灶标注
 */
interface SetShowNodulesAction {
  type: typeof SET_SHOW_NODULES;
  payload: boolean;
}

/**
 * 设置检测状态的Action接口
 */
interface SetDetectStatusAction {
  type: typeof SET_DETECT_STATUS;
  payload: DetectStatus;
}

/**
 * 应用所有可能的Action类型集合
 * 联合类型定义，用于Redux reducer中判断具体的操作类型
 */
export type AppActionTypes =
  | AddImagesAction
  | SetActiveImageAction
  | SetWwAction
  | SetWlAction
  | SetNodulesForImageAction
  | SelectNoduleAction
  | SetShowNodulesAction
  | SetDetectStatusAction;

export type DetectStatus = 'not_started' | 'detecting' | 'detected' | 'not_found';