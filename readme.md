# CT 肺结节检测系统 (Lung Nodule CT CAD)

本项目是一个功能完备的、基于 Web 的医疗影像辅助诊断系统，旨在帮助医疗专业人员高效地检测和分析 CT 影像中的肺部结节。系统采用前后端分离架构，前端负责影像展示与交互，后端负责 AI 模型推理。

---

## 1. 核心功能亮点

-   **真实 AI 模型集成**: 后端集成基于 PyTorch 的 **UNet** 模型，提供精确的结节检测能力。
-   **专业影像支持**: 前端使用 **Cornerstone.js**，原生支持对 DICOM 文件的渲染和交互。
-   **直观的用户体验**:
    -   三栏式布局，集文件管理、主视图、结果分析于一体。
    -   支持窗宽/窗位实时调节，优化图像显示。
    -   检测结果以高亮边界框的形式直接标注在图像上。
    -   提供结节列表和局部放大视图，方便医生逐一查看。
-   **GPU 加速**: 后端能够自动利用 NVIDIA CUDA 进行加速，提升推理效率。

---

## 2. 项目架构

```mermaid
graph TD
    A[用户] --> B{浏览器};
    B --> C[前端 (React + Vite)];
    C -- API请求 --> D[后端 (FastAPI)];
    D -- 调用模型 --> E[AI模型 (PyTorch/UNet)];
    D -- 返回结节坐标 --> C;
    C -- 在图像上标注结节 --> B;

    subgraph "用户端"
        B
    end

    subgraph "前端: ./frontend"
        C
    end

    subgraph "后端: ./backend"
        D
        E
    end
```

---

## 3. 项目结构

-   `./frontend/`: 包含所有前端相关代码。这是一个基于 **React** 和 **Vite** 的 TypeScript 项目。详细信息请参阅 [**前端 README**](./frontend/README.md)。
-   `./backend/`: 包含所有后端相关代码。这是一个基于 **FastAPI** 和 **PyTorch** 的 Python 项目。详细信息请参阅 [**后端 README**](./backend/readme.md)。
-   `./readme.md`: 你正在阅读的这份总览文档。

---

## 4. 如何运行

本项目需要分别启动前端和后端两个服务。

### **步骤 1: 启动后端 AI 服务**

1.  进入后端目录: `cd backend`
2.  安装依赖并启动服务。

> **详细步骤请务必参考 [后端 README](./backend/readme.md) 中的说明，特别是关于 GPU 环境的配置。**

### **步骤 2: 启动前端应用**

1.  打开一个新的终端，进入前端目录: `cd frontend`
2.  安装依赖并启动服务。

> **详细步骤请参考 [前端 README](./frontend/README.md) 中的说明。**

