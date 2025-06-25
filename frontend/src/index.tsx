import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { configureCornerstone } from './cornerstone-init'; // 导入配置函数
import store from '@store/index';
import App from './App';
// 导入全局样式文件：定义应用级别的样式（如重置样式、全局字体等）
import './index.css';
import './assets/buttons.css';

// 初始化 Cornerstone
configureCornerstone();

// 创建根DOM节点（对应HTML中id为"root"的元素，通常是<div id="root"></div>）
// document.getElementById('root')! 中的!是TypeScript的非空断言：告诉编译器该元素一定存在（避免类型错误）
const root = ReactDOM.createRoot(document.getElementById('root')!);

// 渲染应用到DOM
root.render(
  <React.StrictMode>
    {/*包裹Provider组件：将Redux的store注入React组件树
    store属性：传入之前创建的Redux store实例（所有子组件可通过useSelector/connect访问状态）*/}
    <Provider store={store}>
      {/* 应用根组件：所有业务组件的入口 */}
      <App />
    </Provider>
  </React.StrictMode>,
);