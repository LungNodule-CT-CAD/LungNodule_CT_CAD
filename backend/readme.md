# **CT 肺结节检测系统 - AI 后端 API**

## **1. 项目概述**

本项目是一个基于 **FastAPI** 和 **PyTorch** 构建的、具备真实AI推理能力的后端服务器，专为 `CT 肺结节检测系统` 提供核心分析功能。它能够接收医学影像，并通过 **单阶段分割模型 (U-Net)** 直接定位出疑似肺结节的区域。

**核心功能**:
-   **单阶段结节检测**: 提供一个 `/api/predict` 接口，接收前端上传的图像文件（优先支持 DICOM 格式），利用 **U-Net** 模型进行推理，并返回检测到的结节轮廓坐标。
-   **GPU 加速**: 自动检测并利用 `NVIDIA CUDA` 进行 GPU 加速，大幅提升模型推理速度。
-   **专业图像预处理**: 内置专业的 DICOM 图像处理流程，包括应用 Hounsfield Unit (HU) 转换和肺窗（Lung Window）技术，以确保模型接收到最优化的输入。对于非 DICOM 图像，则执行标准灰度处理。
-   **CORS 支持**: 内置跨域资源共享 (CORS) 中间件，允许指定的来源进行请求，方便前后端分离开发。

---

## **2. 技术栈与架构**

-   **Web 框架**: FastAPI
-   **AI 框架**: PyTorch
-   **核心依赖**: Uvicorn, Pydicom, OpenCV-Python, python-multipart
-   **模型架构**: 系统采用在 `unet_model.py` 文件中定义的 **U-Net** 网络结构。这是一个在医学图像分割领域被广泛应用的经典模型。
-   **模型加载**: 在 FastAPI 应用启动时，模型 (`model-best.pth`) 会被自动预加载到内存（优先加载到 GPU），以确保 API 请求的快速响应。

---

## **3. 文件结构**

```
backend/
├── main.py                 # FastAPI 应用主文件，定义 API 端点
├── predict.py              # 核心预测逻辑，包括图像预处理、模型推理和后处理
├── unet_model.py           # U-Net 模型的 PyTorch 定义
├── requirements.txt        # 项目依赖
├── model-best.pth          # (必要) 默认加载的预训练 U-Net 模型权重
├── model-finetuned.pth     # (可选) 另一个预训练模型权重，当前代码未直接使用
└── readme.md               # 项目说明文档
```

---

## **4. 环境设置与运行**

在运行此后端服务器之前，请确保您已安装 Python 3.8+。

1.  **克隆或下载项目到本地。**

2.  **创建并激活虚拟环境 (推荐)**:
    在 `backend` 目录下打开终端，运行以下命令：
    ```bash
    # 创建虚拟环境
    python -m venv venv

    # 激活虚拟环境 (Windows)
    .\\venv\\Scripts\\activate
    
    # 激活 (macOS / Linux)
    # source venv/bin/activate
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```
    *如果希望使用 GPU，请确保已安装与 PyTorch 兼容的 NVIDIA 驱动和 CUDA Toolkit。`requirements.txt` 中的 `torch` 会根据您的环境自动安装相应版本。*

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

## **5. API 接口**

本项目目前提供以下 API 接口：

### **GET /**
-   **功能**: 根路径，用于快速检查服务器是否成功运行。
-   **成功响应 (200 OK)**:
    ```json
    {
        "status": "healthy",
        "message": "Lung Nodule Detection API is running."
    }
    ```

### **POST /api/predict**
-   **功能**: 对上传的单个图像文件执行肺结节检测。
-   **请求**: `multipart/form-data`，包含一个名为 `file` 的文件字段。
-   **处理流程**:
    1.  读取图像字节，优先作为 DICOM 文件处理，应用肺窗和 HU 值转换；如果失败，则作为常规图像（如 PNG/JPG）进行灰度处理。
    2.  将图像归一化、缩放到模型所需的尺寸 (512x512)。
    3.  将处理后的数据送入预加载的 U-Net 模型进行推理，生成分割蒙版 (Mask)。
    4.  对蒙版进行后处理，通过连通域分析过滤掉面积过小的噪声区域。
    5.  提取最终蒙版中各个区域的轮廓。
    6.  将每个结节的轮廓点集格式化为 JSON 返回。
-   **成功响应 (200 OK)**:
    ```json
    {
      "nodules": [
        { 
          "id": 1, 
          "contour": [
            { "x": 150, "y": 200 }, 
            { "x": 151, "y": 200 },
            ...
          ]
        }
      ]
    }
    ```

---
*该 README 已根据最新的单阶段 U-Net 检测流程进行更新。*
