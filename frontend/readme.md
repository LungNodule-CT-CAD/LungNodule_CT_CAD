# **CT 肺结节检测系统 - 前端文档**

## **1. 项目概述**

本项目是 **CT 肺结节检测系统** 的前端部分，基于 **React v19** 和 **Vite** 构建，并全面采用 **TypeScript** 以保证代码的类型安全和可维护性。系统致力于为医疗专业人员提供一个强大、直观的医学影像分析平台。

### **核心功能**
- **多格式图像支持**: 支持 **DICOM (.dcm)** 文件的专业渲染，同时也兼容常规图像格式（如 PNG, JPG）。
- **文件管理与导航**: 用户可以方便地上传多个图像文件，并通过侧边栏的缩略图列表快速切换。
- **智能结节检测**: 用户可针对当前选中的图像，一键调用后端 AI 模型进行肺结节检测，检测结果将以边界框的形式精确标注在图像上。
- **专业图像调窗**: 内置窗宽 (Window Width) 和窗位 (Window Level) 调整功能，允许用户优化 CT 图像的对比度和亮度，以获得最佳视觉效果。
- **结节详情与放大**: 系统会列出当前图像检测到的所有结节。用户可以选中任意结节，在专门的视图中查看其局部放大图像和坐标信息。

---

## **2. 页面与路由**

应用采用 `react-router-dom` 进行路由管理，包含以下两个主要页面：

-   **`/` - 欢迎页面 (`Home.tsx`)**:
    作为应用的入口，提供一个简洁的欢迎界面和一个"开始使用"按钮，引导用户进入主工作区。

-   **`/workspace` - 工作区页面 (`Workspace.tsx`)**:
    这是应用的核心，集成了所有功能组件，提供一个完整的三栏式布局，用于图像查看、分析和交互。

---

## **3. 如何运行**

1.  **克隆或下载项目到本地。**

2.  **安装依赖：**
    在项目根目录下打开终端，运行：
    ```bash
    npm install
    ```

3.  **启动开发服务器：**
    ```bash
    npm run dev
    ```
    启动后，在浏览器中打开提示的地址（通常是 `http://localhost:5173` 或 `http://localhost:3000`）即可访问。

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
│   │   ├── ImageViewer.tsx        # 核心图像显示与标注组件 (Cornerstone.js)
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

-   **`ImageUploader.tsx`**: 负责处理文件上传逻辑，支持用户选择一个或多个本地图像文件。
-   **`ThumbnailList.tsx`**: 以列表形式展示所有已上传图像的缩略图，用户点击即可切换当前活动图像。
-   **`ImageViewer.tsx`**: 应用的核心，使用 **Cornerstone.js** 渲染 DICOM 图像，并根据 Redux store 的数据，绘制结节的边界框。
-   **`WindowAdjuster.tsx`**: 提供两个滑块，允许用户实时调整窗宽和窗位，以优化图像显示。
-   **`NoduleList.tsx`**: 展示当前活动图像中所有已检测到的结节。用户点击列表项可以选择特定结节。
-   **`NoduleLocalZoom.tsx`**: 当用户在 `NoduleList` 中选择一个结节后，此组件会显示该结节区域的放大视图及其详细坐标信息。

---

## **6. 状态管理 (Redux)**

项目采用 **Redux** 进行集中的状态管理，以处理复杂的交互和数据流。

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
    
    interface ImageFile {
      id: string;
      file: File;
      imageUrl: string;
      nodules: Nodule[];
      isDicom: boolean; // 标记是否为 DICOM 文件
    }
    ```
-   **关键 Actions**:
    -   `uploadImages()`: 处理文件上传，将其转换为 `ImageFile` 对象。
    -   `setActiveImage()`: 设置当前活动的图像。
    -   `detectNodules()`: **[异步]** 将当前活动图像发送到后端 API，并在成功后更新该图像的结节列表。
    -   `selectNodule()`: 在本地更新当前选中的结节。

    更详细的数据结构和 Actions 定义，请参阅 `data.md` 文档。

---

## **7. 后端 API 接口**

本项目依赖后端提供结节检测服务。
-   `POST /api/detect-nodules`: 用于对单个图像文件执行结节检测。

详细的 API 请求/响应格式和示例，请参阅 `api.md` 文档。

---

## **8. 样式与主题**

项目采用了一套定制的**深蓝色科技感主题**，以符合医学影像分析的专业氛围。
-   **主背景**: 深海军蓝 (`#0a192f`)
-   **面板/卡片**: 稍亮的蓝色 (`#1c2a4a`)
-   **高亮/交互色**: 明亮的青色 (`#64ffda`)
-   **文本**: 浅灰蓝色 (`#ccd6f6`)
-   主要的全局样式和 CSS 变量定义在 `src/index.css`。

---

## **9. 潜在问题与改进建议**

在开发过程中，我们识别出一些可以进一步优化的地方，以提高代码质量和应用的可扩展性。

-   **配置硬编码 (Hardcoded Configuration)**:
    -   **问题**: 目前，一些工具的配置（如 `ZoomTool` 的缩放范围）和界面元素的样式（如结节标注框的颜色）直接硬编码在组件文件（`ImageViewer.tsx`）中。
    -   **建议**: 将这些配置抽离到一个单独的 `config.ts` 或主题对象 (`theme.ts`) 中。这样做可以使配置更易于管理和修改，而无需深入组件代码。


-   **组件职责过重 (Component Over-Responsibility)**:
    -   **问题**: `ImageViewer.tsx` 组件目前承担了过多的职责，包括 Cornerstone 的初始化、图像加载、事件处理（缩放、拖拽）以及结节标注的渲染。这使得组件变得复杂且难以维护。
    -   **建议**: 对 `ImageViewer.tsx` 进行重构，将不同的功能逻辑拆分到自定义 Hooks 中。例如：
        -   `useCornerstone(elementRef)`: 封装 Cornerstone 元素的启用、禁用和基础配置。
        -   `useImageLoader(elementRef, activeImage)`: 负责图像的加载和显示。
        -   `useNoduleAnnotations(elementRef, activeImage, nodules)`: 专门处理结节标注的清除、添加和更新逻辑。
    通过这种方式，可以使 `ImageViewer` 组件本身更简洁，只负责组合这些 Hooks，从而提高代码的可读性和可复用性。
