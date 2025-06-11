# **CT 肺结节检测系统 - 前端文档**

## **1. 项目概述**
本项目是 CT 肺结节检测系统的前端部分，基于 **React** 和 **Vite** 构建，使用 **TypeScript** 以增强代码的健壮性。前端界面旨在为用户提供一个专业、高效的医学影像分析工具，支持 CT 图像的上传、显示、分析与交互。

核心功能包括：
- **DICOM 图像上传**：用户可以从本地选择并上传 DICOM 格式的 CT 图像。
- **图像渲染与交互**：在画布（Canvas）上清晰地渲染 CT 图像，并支持通过调整**窗宽（WW）**和**窗位（WL）**来优化图像的显示效果。
- **智能结节检测**：与后端 API 集成，对上传的图像执行肺结节检测，并在图像上精确标注出检测到的结节位置。
- **结节详情查看**：在界面侧边栏展示所有检测到的结节列表，用户可以点击列表项切换并放大查看特定结节的细节。

本项目采用前后端分离的 **B/S 架构**，前端负责用户交互和数据可视化，后端（需另外搭建）则提供图像处理、模型推理等计算密集型服务。

---

## **2. 如何运行**

1.  **克隆或下载项目到本地。**

2.  **安装依赖：**
    在项目根目录下打开终端，运行以下命令：
    ```bash
    npm install
    ```

3.  **启动开发服务器：**
    ```bash
    npm run dev
    ```
    启动后，在浏览器中打开提示的地址（通常是 `http://localhost:5173`）即可访问。

---

## **3. 项目结构**
项目遵循模块化的组件设计，具备清晰、可维护的代码结构。

```
/
├── public/
│   └── logo.jpeg              # 静态 Logo 文件
├── src/
│   ├── assets/
│   │   └── styles.css         # 自定义组件样式
│   ├── components/            # 可复用 UI 组件
│   │   ├── ImageUploader.tsx  # 图像上传组件
│   │   ├── ImageViewer.tsx    # 图像显示与标注组件
│   │   ├── WindowAdjuster.tsx # 窗宽/窗位调整组件
│   │   ├── NoduleList.tsx     # 结节列表组件
│   │   └── NoduleZoom.tsx     # 结节放大显示组件
│   ├── pages/
│   │   └── Home.tsx           # 应用主页面，整合所有组件
│   ├── store/                 # Redux 状态管理
│   │   ├── actions.ts         # 定义异步 Actions
│   │   ├── reducers.ts        # 定义 Reducers
│   │   ├── index.ts           # Store 配置
│   │   └── types.ts           # TypeScript 类型定义
│   ├── App.tsx                # 应用根组件
│   ├── index.css              # 全局样式与 CSS 变量
│   ├── index.tsx              # React 应用入口
│   └── main.tsx               # (如果存在，通常是入口)
├── package.json               # 项目依赖和脚本配置
└── vite.config.ts             # Vite 构建配置
```

---

## **4. 核心组件功能**

-   **`ImageUploader.tsx`**: 负责处理文件上传。用户通过此组件选择本地的 DICOM 文件，组件会通过 `axios` 将文件以 `multipart/form-data` 格式发送至后端 `/api/upload` 接口。
-   **`ImageViewer.tsx`**: 系统的核心显示区域。它使用 HTML5 Canvas 渲染 CT 图像，并根据从 Redux store 中获取的结节数据，在图像上绘制矩形框以标注结节。
-   **`WindowAdjuster.tsx`**: 提供两个滑块（Slider），允许用户实时调整窗宽和窗位，并将调整后的参数发送至后端 `/api/adjust-window` 接口，以获取最佳的图像显示效果。
-   **`NoduleList.tsx`**: 以列表形式展示后端检测到的所有肺结节。用户点击列表中的某一项，可以触发状态更新，以便在其他组件中高亮显示该结节。
-   **`NoduleZoom.tsx`**: 一个联动组件，当用户在 `NoduleList` 中选择一个结节后，此组件会显示该结节区域的放大视图，便于用户仔细观察。
-   **`Home.tsx`**: 作为主页面，负责整体布局，将以上所有功能组件有机地整合在一起，构建出完整的用户界面。

---

## **5. 状态管理 (Redux)**
项目使用 **Redux** 进行集中的状态管理，以确保数据在不同组件间的一致性和流畅传递。

-   **State 结构**:
    ```typescript
    interface AppState {
      uploadedImage: string | null;  // 存储后端返回的图像数据 (Base64 或 URL)
      ww: number;                    // 当前窗宽
      wl: number;                    // 当前窗位
      nodules: Nodule[];             // 检测到的结节列表
      selectedNodule: Nodule | null; // 用户当前选中的结节
    }
    ```
-   **Actions**:
    -   `uploadImage(file)`: 异步 action，调用 `/api/upload` 上传文件。
    -   `adjustWindow(ww, wl)`: 异步 action，调用 `/api/adjust-window` 更新窗宽/窗位。
    -   `detectNodules()`: 异步 action，调用 `/api/detect-nodules` 获取结节数据。
    -   `selectNodule(nodule)`: 同步 action，在本地更新当前选中的结节。

---

## **6. 样式与主题**
项目采用了一套定制的**深蓝色科技感主题**，以符合医学影像分析的专业氛围。

-   **设计理念**:
    -   **主背景**: 深海军蓝 (`#0a192f`)，营造沉浸、专注的视觉环境。
    -   **面板/卡片**: 稍亮的蓝色 (`#1c2a4a`)，与背景形成层次感。
    -   **高亮/交互色**: 明亮的青色 (`#64ffda`)，充满科技感。
    -   **文本**: 浅灰蓝色 (`#ccd6f6`)，确保在深色背景下的可读性。
-   **主要样式文件**:
    -   `src/index.css`: 定义全局 CSS 变量（颜色、字体等）和基础样式。
    -   `src/App.css`: 定义应用级的布局和容器样式。
    -   `src/assets/styles.css`: 包含各个自定义组件的详细样式。

---

## **7. 后端 API 接口**
本项目需要后端提供以下 API 接口以保证功能完整：
-   `POST /api/upload`: 用于上传图像文件。
-   `POST /api/adjust-window`: 用于调整窗宽窗位。
-   `POST /api/detect-nodules`: 用于执行结节检测。

更详细的 API 设计请参阅 `api.md` 文档。