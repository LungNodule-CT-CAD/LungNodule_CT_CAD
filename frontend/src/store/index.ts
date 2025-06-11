

// 导入Redux核心工具函数和中间件相关模块
import { applyMiddleware, legacy_createStore } from 'redux';  // Redux创建store和应用中间件的函数
import { thunk, ThunkMiddleware } from 'redux-thunk';         // 用于处理异步action的Redux中间件
import rootReducer from './reducers';                        // 应用的根reducer（状态管理核心逻辑）
import { AppState, AppActionTypes } from './types';          // 应用状态类型和action类型定义


/**
 * 创建Redux store实例（全局状态容器）
 * 负责管理应用的所有状态，并通过reducer处理状态变更
 * 参数说明：
 * - 第一个参数：根reducer（rootReducer），用于定义状态如何响应action变化
 * - 第二个参数：中间件增强器（applyMiddleware），用于扩展Redux功能（此处添加thunk中间件支持异步action）
 */
const store = legacy_createStore(
  rootReducer,  // 根reducer：整合所有子reducer，定义状态树的更新逻辑
  // 应用中间件：此处使用thunk中间件，允许dispatch函数（支持异步操作）
  applyMiddleware(thunk as ThunkMiddleware<AppState, AppActionTypes>)
  // 类型断言说明：将thunk中间件断言为适配当前应用状态（AppState）和action类型（AppActionTypes）的中间件
);


/**
 * 导出全局状态类型（RootState）
 * 通过`ReturnType<typeof store.getState>`自动推导store的状态类型
 * 作用：在组件或其他模块中使用时，可直接引用此类型作为状态的类型注解，避免手动定义重复类型
 */
export type RootState = ReturnType<typeof store.getState>;

/**
 * 导出dispatch类型（AppDispatch）
 * 通过`typeof store.dispatch`获取store的dispatch函数类型
 * 作用：在需要使用dispatch的地方（如组件中），可明确指定dispatch的类型，提供更好的类型提示
 */
export type AppDispatch = typeof store.dispatch;

// 导出store实例（全局唯一的状态容器）
// 其他模块可通过此store访问状态（store.getState()）或分发action（store.dispatch()）
export default store;