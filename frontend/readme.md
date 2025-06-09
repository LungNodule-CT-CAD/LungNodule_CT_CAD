# **基于 React 的 CT 肺结节检测系统前端开发文档**

## **1. 引言**
本项目旨在开发一个基于 React 的前端界面，用于 CT 肺结节检测系统。系统支持用户上传 CT 图像、调整窗宽窗位、检测并标注肺结节、切换显示多个结节等功能。采用 B/S 架构，前端通过 React 实现，后端提供 API 支持图像处理和模型推理。项目使用 Vite 作为构建工具，结合 TypeScript 和 SWC 优化开发效率。

---

## **2. 需求文档**

### **2.1 功能需求**
系统需实现以下核心功能：
1. **图像上传**：支持用户上传本地 DICOM 格式的 CT 图像。
2. **图像显示**：在界面上显示上传的 CT 图像，支持用户调整窗宽（WW）和窗位（WL）以优化显示效果。
3. **结节检测**：对上传的图像进行肺结节检测，并在图像上标注检测结果。
4. **结节切换与放大**：支持用户选择并切换查看多个检测到的结节，并放大显示选中的结节区域。

### **2.2 非功能需求**
- **易用性**：界面直观，操作简单。
- **响应性**：适配不同设备和浏览器。
- **性能**：图像加载和处理高效，窗宽窗位调整实时更新。
- **安全性**：保护用户上传的数据，不在前端存储敏感信息。

---

## **3. 项目结构建议**
项目基于 React，使用 React Router 管理页面，Redux 管理状态。以下是推荐的项目结构：

```
lung-nodule-detection-frontend/
├── public/                      # 静态资源
│   ├── index.html              # 主 HTML 文件
│   └── assets/                 # 静态图像、图标等
│       └── logo.png            # 系统 Logo
├── src/                        # 源代码
│   ├── assets/                 # 项目样式、图片等
│   │   └── styles.css          # 全局样式
│   ├── components/             # 可复用组件
│   │   ├── ImageUploader.tsx   # 图像上传组件
│   │   ├── ImageViewer.tsx     # 图像显示组件
│   │   ├── WindowAdjuster.tsx  # 窗宽窗位调整组件
│   │   ├── NoduleList.tsx      # 结节列表组件
│   │   └── NoduleZoom.tsx      # 结节放大组件
│   ├── pages/                  # 页面级组件
│   │   └── Home.tsx            # 主页面
│   ├── store/                  # Redux 状态管理
│   │   ├── actions.ts          # 定义 actions
│   │   ├── reducers.ts         # 定义 reducers
│   │   └── index.ts            # Redux store 配置
│   ├── App.tsx                 # 根组件
│   ├── index.tsx               # React 入口
│   └── router.tsx              # React Router 配置（可选）
├── package.json                # 项目依赖和脚本
├── vite.config.ts              # Vite 配置
├── tsconfig.json               # TypeScript 配置
├── .gitignore                  # Git 忽略文件
└── README.md                   # 项目说明
```

---

## **4. 组件功能说明**

### **4.1 ImageUploader.tsx**
- **功能**：支持用户上传 DICOM 文件并发送至后端。
- **实现**：
  - 使用 `<input type="file">` 捕获文件。
  - 通过 `axios` 发送文件至后端 API（`POST /upload`）。
  - 将返回的图像数据存入 Redux。
- **输出**：更新 Redux 的 `uploadedImage` 状态。

### **4.2 ImageViewer.tsx**
- **功能**：显示 CT 图像并支持结节标注。
- **实现**：
  - 使用 `<canvas>` 渲染图像，支持动态调整显示。
  - 根据 Redux 的 `nodules` 数据绘制结节框。
- **依赖**：Redux 的 `uploadedImage` 和 `nodules`。

### **4.3 WindowAdjuster.tsx**
- **功能**：调整窗宽（WW）和窗位（WL）。
- **实现**：
  - 使用滑块（`<input type="range">`）调整 WW/WL。
  - 调用后端 API（`POST /adjust-window`）更新图像。
- **默认值**：WW: 1500 HU，WL: -600 HU。

### **4.4 NoduleList.tsx**
- **功能**：展示检测到的结节列表，支持选择。
- **实现**：
  - 使用按钮或列表展示结节。
  - 点击后更新 Redux 的 `selectedNodule`。
- **依赖**：Redux 的 `nodules`。

### **4.5 NoduleZoom.tsx**
- **功能**：放大显示选中的结节区域。
- **实现**：
  - 根据 `selectedNodule` 坐标裁剪并放大图像。
  - 提供切换按钮更新 `selectedNodule`。
- **依赖**：与 `NoduleList` 联动。

### **4.6 Home.tsx**
- **功能**：整合所有组件，提供整体布局。
- **布局**：
  - 顶部：系统名称、Logo。
  - 左侧：工具栏（上传、调整 WW/WL、检测）。
  - 中间：图像显示区。
  - 右侧：结节列表和放大区。

---

## **5. 状态管理（Redux）**

### **5.1 状态结构**
```typescript
interface State {
  uploadedImage: string | null;  // 图像数据（base64 格式）
  ww: number;                    // 窗宽
  wl: number;                    // 窗位
  nodules: Array<{ id: number; x: number; y: number; width: number; height: number }>; // 结节列表
  selectedNodule: { id: number; x: number; y: number; width: number; height: number } | null; // 当前选中结节
}
```

### **5.2 Actions**
- **uploadImage(file: File)**：上传图像，更新 `uploadedImage`。
- **adjustWindow(ww: number, wl: number)**：调整 WW/WL，更新图像。
- **detectNodules()**：检测结节，更新 `nodules`。
- **selectNodule(nodule: { id: number; x: number; y: number; width: number; height: number } | null)**：选择结节，更新 `selectedNodule`。

### **5.3 Reducers**
```typescript
import { Reducer } from 'redux';

const initialState: State = {
  uploadedImage: null,
  ww: 1500,
  wl: -600,
  nodules: [],
  selectedNodule: null,
};

const rootReducer: Reducer<State> = (state = initialState, action) => {
  switch (action.type) {
    case 'SET_IMAGE':
      return { ...state, uploadedImage: action.payload };
    case 'SET_WW':
      return { ...state, ww: action.payload };
    case 'SET_WL':
      return { ...state, wl: action.payload };
    case 'SET_NODULES':
      return { ...state, nodules: action.payload };
    case 'SELECT_NODULE':
      return { ...state, selectedNodule: action.payload };
    default:
      return state;
  }
};

export default rootReducer;
```

### **5.4 示例代码**
```typescript
// actions.ts
import { Dispatch } from 'redux';
import axios from 'axios';

export const uploadImage = (file: File) => async (dispatch: Dispatch) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post('/api/upload', formData);
  dispatch({ type: 'SET_IMAGE', payload: response.data.image });
};

export const adjustWindow = (ww: number, wl: number) => async (dispatch: Dispatch, getState: any) => {
  const { uploadedImage } = getState();
  const response = await axios.post('/api/adjust-window', { ww, wl, image: uploadedImage });
  dispatch({ type: 'SET_IMAGE', payload: response.data.image });
  dispatch({ type: 'SET_WW', payload: ww });
  dispatch({ type: 'SET_WL', payload: wl });
};

export const detectNodules = () => async (dispatch: Dispatch, getState: any) => {
  const { uploadedImage } = getState();
  const response = await axios.post('/api/detect-nodules', { image: uploadedImage });
  dispatch({ type: 'SET_NODULES', payload: response.data.nodules });
};

export const selectNodule = (nodule: { id: number; x: number; y: number; width: number; height: number } | null) => ({
  type: 'SELECT_NODULE',
  payload: nodule,
});
```

---

## **6. 开发流程建议**
1. **初始化项目**：运行 `npm create vite@latest . -- --template react-ts`。
2. **安装依赖**：`npm install redux react-redux @types/react-redux redux-thunk @types/redux-thunk axios @types/axios react-router-dom @types/react-router-dom swc-loader`.
3. **组件开发**：按上述说明逐一实现 `.tsx` 组件。
4. **状态管理**：配置 Redux，测试 TypeScript 类型安全。
5. **API 联调**：与后端对接，确保功能正常。
6. **样式优化**：使用 Tailwind CSS 或 CSS 文件美化界面。
7. **测试**：验证功能完整性和性能。

---

## **7. 参考资源**
- React: https://reactjs.org/
- Vite: https://vitejs.dev/
- TypeScript: https://www.typescriptlang.org/
- SWC: https://swc.rs/
- Redux: https://redux.js.org/
- Axios: https://axios-http.com/
- Tailwind CSS: https://tailwindcss.com/

---

## **8. 结语**
本文档提供了基于 Vite + React + TypeScript + SWC 的 CT 肺结节检测系统前端开发的完整指南。遵循建议的项目结构和状态管理方案，可高效完成开发任务。如需进一步支持，请联系后端团队。

**开发团队**：（待填写）  
**日期**：2025 年 6 月 9 日