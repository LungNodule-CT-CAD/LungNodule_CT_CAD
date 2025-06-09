import { applyMiddleware, legacy_createStore } from 'redux';
import { thunk, ThunkMiddleware } from 'redux-thunk';
import rootReducer from './reducers';
import { AppState, AppActionTypes } from './types';

const store = legacy_createStore(
  rootReducer,
  applyMiddleware(thunk as ThunkMiddleware<AppState, AppActionTypes>)
);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;
