# **CT 肺结节检测系统 - 前端文档**

## **1. 项目概述**
本项目是 CT 肺结节检测系统的前端部分，基于 **React** 和 **Vite** 构建，使用 **TypeScript** 以增强代码的健壮性。前端界面旨在为用户提供一个专业、高效的医学影像分析工具，支持 CT 图像的上传、显示、分析与交互。

核心功能包括：
- **多图像上传与管理**：用户可以一次性从本地选择并上传**多张**图像（支持 DICOM, PNG, JPG 等格式）。
- **缩略图导航**：上传的图像会以缩略图形式在侧边栏展示，用户可以方便地点击切换当前需要分析的图像。
- **按需智能结节检测**：用户选择一张图像后，可点击"开始预测"按钮。前端将**仅针对当前选中的图像**调用后端 API 执行肺结节检测，并将结果精确标注在图像上。
- **图像渲染与交互**：在画布（Canvas）上清晰地渲染 CT 图像，并支持通过调整**窗宽（WW）**和**窗位（WL）**来优化图像的显示效果。
- **结节详情查看**：在界面侧边栏展示当前图像检测到的结节列表，用户可以点击列表项高亮显示特定结节。

本项目采用前后端分离的 **B/S 架构**，前端负责用户交互和数据可视化，后端（需另外搭建）则提供模型推理等计算密集型服务。

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
    启动后，在浏览器中打开提示的地址（通常是 `http://localhost:3000`）即可访问。

---

## **3. 项目结构**
项目遵循模块化的组件设计，具备清晰、可维护的代码结构。

```
/
├── public/
│   └── logo.jpeg
├── src/
│   ├── assets/
│   ├── components/            # 可复用 UI 组件
│   │   ├── ImageUploader.tsx  # 多图像上传组件
│   │   ├── ThumbnailList.tsx  # 图像缩略图列表组件
│   │   ├── ImageViewer.tsx    # 图像显示与标注组件
│   │   ├── WindowAdjuster.tsx # 窗宽/窗位调整组件
│   │   ├── NoduleList.tsx     # 结节列表组件
│   │   └── NoduleZoom.tsx     # 结节放大显示组件
│   ├── pages/
│   │   └── Workspace.tsx      # 应用主工作区页面，整合所有组件
│   ├── store/                 # Redux 状态管理
│   │   ├── actions.ts
│   │   ├── reducers.ts
│   │   ├── index.ts
│   │   └── types.ts
│   ├── App.tsx
│   ├── index.css
│   └── index.tsx
├── package.json
└── vite.config.ts
```

---

## **4. 核心组件功能**

-   **`ImageUploader.tsx`**: 负责处理多文件上传。用户通过此组件选择本地的一个或多个图像文件。
-   **`ThumbnailList.tsx`**: 显示所有已上传图像的缩略图。用户点击缩略图可以切换**活动图像**。
-   **`ImageViewer.tsx`**: 系统的核心显示区域。它使用 HTML5 Canvas 渲染当前**活动图像**，并根据 Redux store 中该图像关联的结节数据，绘制矩形框进行标注。
-   **`WindowAdjuster.tsx`**: 提供滑块让用户调整窗宽和窗位，这些参数目前在前端全局生效，用于调整图像显示。
-   **`NoduleList.tsx`**: 以列表形式展示当前**活动图像**检测到的所有肺结节。
-   **`NoduleZoom.tsx`**: 一个联动组件，当用户在 `NoduleList` 中选择一个结节后，此组件未来可以显示该结节区域的放大视图。
-   **`Workspace.tsx`**: 作为主页面，负责整体三栏式布局，将以上所有功能组件有机地整合在一起，构建出完整的用户界面。

---

## **5. 状态管理 (Redux)**
项目使用 **Redux** 进行集中的状态管理，以支持多图像工作流。

-   **State 结构**:
    ```typescript
    interface AppState {
      images: ImageFile[];          // 存储所有上传的图像对象
      activeImageId: string | null; // 当前活动图像的ID
      ww: number;                   // 窗宽
      wl: number;                   // 窗位
      selectedNodule: Nodule | null;// 当前选中的结节
      showNodules: boolean;         // 是否显示结节
    }
    
    interface ImageFile {
      id: string;      // 唯一ID
      file: File;      // 原始文件
      imageUrl: string;// 本地预览URL
      nodules: Nodule[];// 关联的结节列表
    }
    ```
-   **核心 Actions**:
    -   `uploadImages(files)`: 异步 action，在本地处理多文件上传并更新状态。
    -   `setActiveImage(imageId)`: 同步 action，设置当前活动的图像。
    -   `detectNodules()`: 异步 action，将**当前活动图像**的文件发送到 `/api/detect-nodules` 并获取结节数据。
    -   `selectNodule(nodule)`: 同步 action，在本地更新当前选中的结节。

---

## **6. 样式与主题**
项目采用了一套定制的**深蓝色科技感主题**，以符合医学影像分析的专业氛围。

-   **设计理念**:
    -   **主背景**: 深海军蓝 (`#0a192f`)。
    -   **面板/卡片**: 稍亮的蓝色 (`#1c2a4a`)。
    -   **高亮/交互色**: 明亮的青色 (`#64ffda`)。
    -   **文本**: 浅灰蓝色 (`#ccd6f6`)。
-   **主要样式文件**:
    -   `src/index.css`: 定义全局 CSS 变量。
    -   `src/App.css`: 定义应用级的布局样式。

---

## **7. 后端 API 接口**
本项目需要后端提供以下 API 接口以保证功能完整：
-   `POST /api/detect-nodules`: 用于对单个图像文件执行结节检测。

更详细的 API 设计请参阅 `api.md` 文档。