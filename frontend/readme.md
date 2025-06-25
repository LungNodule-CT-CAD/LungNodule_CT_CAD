# **CT 肺结节检测系统 - 前端文档（2024升级版）**

## **1. 项目概述**

本项目是 **CT 肺结节检测系统** 的前端部分，基于 **React v19** 和 **Vite** 构建，并全面采用 **TypeScript**。系统致力于为医疗专业人员提供一个强大、直观的医学影像分析平台。

### **核心功能**
- **多格式图像支持**: 支持 **DICOM (.dcm)** 文件的专业渲染，同时也兼容常规图像格式（如 PNG, JPG）。
- **文件管理与导航**: 用户可以方便地上传多个图像文件，并通过侧边栏的缩略图列表快速切换。
- **智能结节检测**: 用户可针对当前选中的图像，一键调用后端 AI 模型进行肺结节检测，检测结果以**真实轮廓**的形式精准标注在图像上。
- **高性能canvas标注**: 前端采用双canvas分层渲染，底层为医学影像，顶层canvas实时绘制所有结节轮廓，支持高亮、缩放、平移等交互。
- **专业图像调窗**: 内置窗宽 (Window Width) 和窗位 (Window Level) 调整功能，允许用户优化 CT 图像的对比度和亮度。
- **结节详情与放大**: 系统会列出当前图像检测到的所有结节。用户可以选中任意结节，在专门的视图中查看其局部放大图像和轮廓。

---

## **2. 页面与路由**

应用采用 `react-router-dom` 进行路由管理，包含以下两个主要页面：

-   **`/` - 欢迎页面 (`Home.tsx`)**: 入口页。
-   **`/workspace` - 工作区页面 (`Workspace.tsx`)**: 应用核心，集成所有功能组件，三栏式布局。

---

## **3. 如何运行**

1.  **克隆或下载项目到本地。**
2.  **安装依赖：**
    ```bash
    npm install
    ```
3.  **启动开发服务器：**
    ```bash
    npm run dev
    ```
    启动后，在浏览器中打开提示的地址（如 `http://localhost:5173`）。

---

## **4. 项目结构**

```
/
├── public/
├── src/
│   ├── assets/
│   ├── components/                # 可复用 UI 组件
│   │   ├── ImageUploader.tsx      # 图像上传组件
│   │   ├── ThumbnailList.tsx      # 图像缩略图列表
│   │   ├── ImageViewer.tsx        # 核心图像显示与canvas轮廓标注组件
│   │   ├── WindowAdjuster.tsx     # 窗宽 (WW) / 窗位 (WL) 调整组件
│   │   ├── NoduleList.tsx         # 检测到的结节列表
│   │   └── NoduleLocalZoom.tsx    # 选中结节的局部放大组件
│   ├── pages/                     # 页面级组件
│   │   ├── Home.tsx               # 欢迎页
│   │   └── Workspace.tsx          # 主工作区页
│   ├── store/                     # Redux 状态管理
│   │   ├── actions.ts
│   │   ├── reducers.ts
│   │   ├── types.ts
│   │   └── index.ts
│   ├── cornerstone-init.ts      # Cornerstone.js 初始化配置
│   ├── router.tsx                 # 路由配置
│   ├── App.tsx
│   └── index.tsx
├── package.json
└── vite.config.ts
```

---

## **5. 核心组件功能**
-   **`ImageUploader.tsx`**: 负责文件上传。
-   **`ThumbnailList.tsx`**: 展示所有已上传图像的缩略图。
-   **`ImageViewer.tsx`**: 应用核心，底层用 cornerstone 渲染 DICOM 图像，顶层 canvas 实时绘制所有结节轮廓，支持高亮、缩放、平移。
-   **`WindowAdjuster.tsx`**: 实时调整窗宽和窗位。
-   **`NoduleList.tsx`**: 展示所有检测到的结节，支持点击高亮。
-   **`NoduleLocalZoom.tsx`**: 局部放大选中结节，canvas 绘制轮廓。

---

## **6. 状态管理 (Redux)**

-   **核心 State 结构 (`AppState`)**:
    ```typescript
    interface AppState {
      images: ImageFile[];
      activeImageId: string | null;
      ww: number;
      wl: number;
      selectedNodule: Nodule | null;
      showNodules: boolean;
    }
    interface Nodule {
      id: number;
      contour: Array<{ x: number; y: number; }>;
    }
    interface ImageFile {
      id: string;
      file: File;
      imageUrl: string;
      nodules: Nodule[];
      isDicom: boolean;
    }
    ```
-   **关键 Actions**:
    -   `uploadImages()`: 处理文件上传。
    -   `setActiveImage()`: 设置当前活动图像。
    -   `detectNodules()`: **[异步]** 将当前活动图像发送到后端 API (`/api/predict`)，并在成功后更新该图像的结节列表。
    -   `selectNodule()`: 更新当前高亮结节。

---

## **7. 后端 API 接口**

-   `POST /api/predict`: 用于对单个图像文件执行结节检测，返回结节的**轮廓点集**。
-   响应格式：
    ```json
    {
      "nodules": [
        { "id": 1, "contour": [ {"x":100,"y":120}, ... ] },
        { "id": 2, "contour": [ {"x":200,"y":220}, ... ] }
      ]
    }
    ```
-   详细说明见 `api.md`。

---

## **8. 标注与交互说明**
- 前端所有结节标注均通过 canvas 绘制，不再依赖 cornerstone-tools 标注系统。
- 主图像区采用双canvas分层渲染，底层为医学影像，顶层canvas绘制所有结节轮廓。
- 轮廓高亮、缩放、平移、切换等交互全部实时同步。
- 局部放大区同样基于 contour 点集绘制。

---

## **9. 样式与主题**
- 深蓝色科技感主题，主背景 `#0a192f`，高亮色 `#64ffda`，文本 `#ccd6f6`。
- 主要全局样式和 CSS 变量定义在 `src/index.css`。

## 结节检测状态交互说明

### 检测状态说明
- **未开始检测（not_started）**：未点击"开始预测"前，右侧不显示任何结节相关内容。
- **检测中（detecting）**：点击"开始预测"后，显示"检测中..."提示。
- **检测到结节（detected）**：检测完成且有结节时，显示"检测到的结节列表"及结节详情。
- **未检测到结节（not_found）**：检测完成但未检测到结节时，显示"当前图像未检测到结节"。

### 使用方法
1. 上传并选择一张CT图像。
2. 点击右侧"开始预测"按钮。
3. 检测过程中会有"检测中..."提示。
4. 检测完成后，根据结果自动显示结节列表或未检测到结节的提示。

### 交互优化说明
- 检测未开始时，避免无意义提示，界面更简洁。
- 检测中有明确进度反馈，提升用户体验。
- 检测结果分情况展示，用户一目了然。
