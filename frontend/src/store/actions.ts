import axios from 'axios';
import { Dispatch } from 'redux';
import { ThunkAction } from 'redux-thunk';
import { AppActionTypes, AppState, Nodule, SELECT_NODULE, SET_IMAGE, SET_NODULES, SET_WW, SET_WL } from './types';

// uploadImage action: Handles file upload and dispatches actions based on the API response.
export const uploadImage =
  (file: File): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<AppActionTypes>) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      // Backend API endpoint for file upload
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      // Dispatch action to update image in the store
      dispatch({ type: SET_IMAGE, payload: response.data.image });
    } catch (error) {
      console.error('Error uploading image:', error);
      // Optionally dispatch an error action to the store
    }
  };

// adjustWindow action: Adjusts window width and level
export const adjustWindow =
  (ww: number, wl: number): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<any>, getState: () => AppState) => {
    const { uploadedImage } = getState();
    if (uploadedImage) {
      try {
        const response = await axios.post('/api/adjust-window', { ww, wl, image: uploadedImage });
        dispatch({ type: SET_IMAGE, payload: response.data.image });
        dispatch({ type: SET_WW, payload: ww });
        dispatch({ type: SET_WL, payload: wl });
      } catch (error) {
        console.error('Error adjusting window:', error);
      }
    }
  };

// detectNodules action: Detects nodules in the uploaded image
export const detectNodules =
  (): ThunkAction<void, AppState, unknown, AppActionTypes> =>
  async (dispatch: Dispatch<any>, getState: () => AppState) => {
    const { uploadedImage } = getState();
    if (uploadedImage) {
      try {
        const response = await axios.post('/api/detect-nodules', { image: uploadedImage });
        dispatch({ type: SET_NODULES, payload: response.data.nodules });
      } catch (error) {
        console.error('Error detecting nodules:', error);
      }
    }
  };

// selectNodule action: Selects a nodule from the list
export const selectNodule = (nodule: Nodule | null): AppActionTypes => ({
  type: SELECT_NODULE,
  payload: nodule,
});
