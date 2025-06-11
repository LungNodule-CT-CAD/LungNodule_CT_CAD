// src/store/types.ts

/**
 * 定义图像中病灶区域的结构接口
 * 用于描述医学影像（如CT/MRI）中标记的病灶位置和尺寸信息
 */
export interface Nodule {
    id: number;           // 病灶唯一标识ID（用于区分不同病灶）
    x: number;            // 病灶区域左上角在图像中的X坐标（像素单位）
    y: number;            // 病灶区域左上角在图像中的Y坐标（像素单位）
    width: number;        // 病灶区域的宽度（像素单位）
    height: number;       // 病灶区域的高度（像素单位）
  }
  
  /**
   * 定义应用的根状态结构
   * 包含应用运行时需要全局管理的所有核心数据
   */
  export interface AppState {
    uploadedImage: string | null;  // 已上传的医学影像文件路径（base64或URL，null表示未上传）
    ww: number;                     // 窗宽（Window Width）- 用于控制图像对比度的参数
    wl: number;                     // 窗位（Window Level）- 用于控制图像亮度的参数
    nodules: Nodule[];              // 当前图像中所有标记的病灶区域列表
    selectedNodule: Nodule | null;  // 当前选中的病灶（null表示未选择任何病灶）
  }
  
  // 定义所有可能的Action类型常量（用于标识状态操作类型）
  export const SET_IMAGE = 'SET_IMAGE';      // 触发"设置上传图像"操作的标识
  export const SET_WW = 'SET_WW';            // 触发"设置窗宽"操作的标识
  export const SET_WL = 'SET_WL';            // 触发"设置窗位"操作的标识
  export const SET_NODULES = 'SET_NODULES';  // 触发"设置病灶列表"操作的标识
  export const SELECT_NODULE = 'SELECT_NODULE'; // 触发"选择病灶"操作的标识
  
  /**
   * 设置上传图像的Action接口
   * 用于将上传的图像路径更新到状态中
   */
  interface SetImageAction {
    type: typeof SET_IMAGE;  // 操作类型（固定为SET_IMAGE）
    payload: string;         // 携带的数据：新的图像路径（base64字符串或URL）
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
   * 设置病灶列表的Action接口
   * 用于更新图像中所有标记的病灶区域数据
   */
  interface SetNodulesAction {
    type: typeof SET_NODULES;  // 操作类型（固定为SET_NODULES）
    payload: Nodule[];         // 携带的数据：新的病灶列表数组
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
   * 应用所有可能的Action类型集合
   * 联合类型定义，用于Redux reducer中判断具体的操作类型
   */
  export type AppActionTypes =
    | SetImageAction
    | SetWwAction
    | SetWlAction
    | SetNodulesAction
    | SelectNoduleAction;