# **CT 肺结节检测系统 - AI 后端 API**

## **1. 项目概述**

本项目是一个基于 **FastAPI** 和 **PyTorch** 构建的、具备真实AI推理能力的后端服务器，专为 `CT 肺结节检测系统` 提供核心分析功能。它取代了原有的模拟 (Mock) API，能够接收医学影像并执行真实的肺结节检测。

**核心功能**:
-   **真实结节检测**: 提供一个 `/api/detect-nodules` 接口，接收前端上传的图像文件（优先支持 DICOM 格式），利用 **UNet** 模型进行推理，并返回检测到的结节边界框坐标。
-   **GPU 加速**: 能够自动检测并利用 `NVIDIA CUDA` 进行 GPU 加速，大幅提升模型推理速度。
-   **专业图像预处理**: 内置专业的 DICOM 图像处理流程，包括应用 Hounsfield Unit (HU) 转换和肺窗（Lung Window）技术，以确保模型接收到最优化的输入。
-   **CORS 支持**: 内置跨域资源共享 (CORS) 中间件，允许来自前端开发服务器的请求。

---

## **2. 模型架构**

-   **模型结构**: 系统采用在 `model.py` 文件中定义的 **UNet** 网络结构。这是一个在医学图像分割领域被广泛应用的经典模型。
-   **模型权重**: 系统会加载 `best_model.pth` 文件中存储的预训练权重。
-   **加载机制**: 在 FastAPI 应用启动时，模型会被自动加载到内存（优先加载到 GPU），以确保首次 API 请求的响应速度。

---

## **3. 环境设置与运行**

在运行此后端服务器之前，请确保您已安装 Python 3.7+ 和 NVIDIA 显卡驱动（若希望使用 GPU）。

1.  **克隆或下载项目到本地。**

2.  **创建并激活虚拟环境 (推荐)**:
    在 `backend` 目录下打开终端，运行以下命令：
    ```bash
    # 创建虚拟环境
    python -m venv venv

    # 激活虚拟环境 (Windows)
    .\\venv\\Scripts\\activate
    # 激活 (macOS / Linux)
    source venv/bin/activate
    ```

3.  **安装依赖:**
    为确保能使用 GPU，推荐按以下步骤安装：
    ```bash
    # 卸载可能存在的 CPU 版本的 torch
    pip uninstall torch torchvision -y

    # 安装 GPU 版本的 torch (以 CUDA 12.1 为例)
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

    # 安装其余依赖
    pip install -r requirements.txt
    ```
    *如果你的机器没有 NVIDIA GPU，可以直接运行 `pip install -r requirements.txt` 来安装 CPU 版本。*

4.  **启动开发服务器：**
    在 `backend` 目录下，运行以下命令来启动 FastAPI 服务器：
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    -   `--reload` 参数会使服务器在代码变更后自动重启。
    -   服务器运行在 `8000` 端口。

5.  **访问 API 文档**:
    服务器启动后，您可以在浏览器中访问 `http://localhost:8000/docs` 查看由 FastAPI 自动生成的交互式 API 文档 (Swagger UI)。

---

## **4. API 接口**

本项目目前提供以下 API 接口：

### **GET /**
-   **功能**: 根路径，用于快速检查服务器是否成功运行。
-   **成功响应 (200 OK)**:
    ```json
    {
      "message": "CT Nodule Detection Mock API is running."
    }
    ```

### **POST /api/detect-nodules**
-   **功能**: 对上传的单个图像文件执行真实的肺结节检测。
-   **请求**: `multipart/form-data`，包含一个名为 `file` 的文件字段。
-   **处理流程**:
    1.  读取图像字节。
    2.  进行预处理（DICOM肺窗应用、归一化、缩放）。
    3.  将处理后的数据送入 UNet 模型进行推理，生成分割蒙版 (Mask)。
    4.  对蒙版进行后处理，提取轮廓并计算外接矩形。
    5.  将矩形坐标格式化为 JSON 返回。
-   **成功响应 (200 OK)**:
    ```json
    {
      "nodules": [
        { "id": 1, "x": 150, "y": 200, "width": 20, "height": 20 },
        { "id": 2, "x": 250, "y": 300, "width": 25, "height": 25 }
      ]
    }
    ```

---
*该 README 由 AI 工程师在完成模型集成任务后自动生成和更新。*
