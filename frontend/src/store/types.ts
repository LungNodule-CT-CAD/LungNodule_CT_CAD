// src/store/types.ts

// 定义应用的状态结构
export interface Nodule {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AppState {
  uploadedImage: string | null;
  ww: number;
  wl: number;
  nodules: Nodule[];
  selectedNodule: Nodule | null;
}

// 定义 Action 的类型
export const SET_IMAGE = 'SET_IMAGE';
export const SET_WW = 'SET_WW';
export const SET_WL = 'SET_WL';
export const SET_NODULES = 'SET_NODULES';
export const SELECT_NODULE = 'SELECT_NODULE';

interface SetImageAction {
  type: typeof SET_IMAGE;
  payload: string;
}

interface SetWwAction {
  type: typeof SET_WW;
  payload: number;
}

interface SetWlAction {
  type: typeof SET_WL;
  payload: number;
}

interface SetNodulesAction {
  type: typeof SET_NODULES;
  payload: Nodule[];
}

interface SelectNoduleAction {
  type: typeof SELECT_NODULE;
  payload: Nodule | null;
}

export type AppActionTypes =
  | SetImageAction
  | SetWwAction
  | SetWlAction
  | SetNodulesAction
  | SelectNoduleAction; 