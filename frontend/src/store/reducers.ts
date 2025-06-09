import { Reducer } from 'redux';
import { AppState, AppActionTypes, SELECT_NODULE, SET_IMAGE, SET_NODULES, SET_WL, SET_WW } from './types';

const initialState: AppState = {
  uploadedImage: null,
  ww: 1500,
  wl: -600,
  nodules: [],
  selectedNodule: null,
};

const rootReducer: Reducer<AppState, AppActionTypes> = (state = initialState, action): AppState => {
  switch (action.type) {
    case SET_IMAGE:
      return { ...state, uploadedImage: action.payload };
    case SET_WW:
      return { ...state, ww: action.payload };
    case SET_WL:
      return { ...state, wl: action.payload };
    case SET_NODULES:
      return { ...state, nodules: action.payload };
    case SELECT_NODULE:
      return { ...state, selectedNodule: action.payload };
    default:
      return state;
  }
};

export default rootReducer;
