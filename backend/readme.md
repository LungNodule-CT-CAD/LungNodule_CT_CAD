# **CT 肺结节检测系统 - 后端模拟服务器文档**

## **1. 项目概述**
本项目是一个基于 **FastAPI** 构建的轻量级后端模拟服务器（Mock Server），专门用于配合 **CT 肺结节检测系统前端** 进行开发与测试。

它的核心目标是模拟真实后端的 API 接口，为前端提供必要的测试数据，使得前端开发者可以在没有真实后端的情况下，独立完成所有核心功能的调试，包括：
- 图像上传与显示
- 窗宽（WW）与窗位（WL）调整
- 肺结节检测与结果标注

本服务器严格遵循 `api.md` 文档中定义的接口规范，确保与前端的顺畅通信。

---

## **2. 如何运行**

1.  **环境准备**:
    确保您已安装 Python (建议版本 3.8+)。

2.  **创建并进入目录**:
    在您的项目根目录（例如 `D:\future\vscode-py\LungNodule_CT_CAD`）下创建 `backend` 文件夹，并将本文件及 `main.py`, `requirements.txt` 放入其中。

3.  **安装依赖**:
    在 `backend` 目录下打开终端，运行以下命令安装所需依赖：
    ```bash
    pip install -r requirements.txt
    ```

4.  **启动开发服务器**:
    在终端中继续运行以下命令：
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    - `--host 0.0.0.0` 允许局域网内的其他设备访问。
    - `--port 8000` 指定服务运行在 8000 端口。
    - `--reload` 开启热重载，当代码文件发生变化时，服务器会自动重启。

    服务器成功启动后，您将在终端看到类似 `Uvicorn running on http://0.0.0.0:8000` 的提示。

---

## **3. 基础 URL (Base URL)**
在前端应用中配置 API 请求时，请使用以下基础 URL：
- **`http://localhost:8000`**

所有 API 请求都应基于此地址。例如，上传图像的完整地址为 `http://localhost:8000/api/upload`。

---

## **4. API 接口实现**

本模拟服务器实现了以下三个核心接口：

### **4.1 `POST /api/upload`**
- **功能**: 接收前端上传的DICOM或标准图像文件。
- **模拟逻辑**: 服务器接收到文件后，会进行智能判断。如果是 DICOM 文件，会应用专业的 VOI LUT（值兴趣查找表）来优化初始显示效果；如果是普通图片，则直接使用。最终，图像统一转换为 PNG 格式，编码为 Base64 字符串，以 JSON 格式返回。

### **4.2 `POST /api/adjust-window`**
- **功能**: 根据指定的窗宽（WW）和窗位（WL）调整图像的对比度和亮度。
- **模拟逻辑**: 此接口现在执行**真实的窗宽窗位调整**。服务器会解码收到的图像数据，利用 NumPy 库对每个像素应用窗宽窗位变换算法，然后生成一张新的、经过调整的图像，并将其以 Base64 格式返回。这为前端提供了即时的、所见即所得的调整体验。

### **4.3 `POST /api/detect-nodules`**
- **功能**: 模拟肺结节检测过程。
- **模拟逻辑**: 这是模拟的核心。当此接口被调用时，服务器**不会进行任何真实的图像分析**。相反，它会：
    1. 随机生成 3 个结节（Nodule）对象。
    2. 每个结节对象包含 `id` 和随机生成的坐标（`x`, `y`）与尺寸（`width`, `height`）。
    3. 将这个包含3个结节的数组以 JSON 格式返回给前端。

    这个过程完美地模拟了模型成功检测到多个结节的场景，使前端可以测试其标注和列表显示功能。

---

## **5. 技术栈**
- **[FastAPI](https://fastapi.tiangolo.com/)**: 高性能的 Python Web 框架。
- **[Uvicorn](https://www.uvicorn.org/)**: ASGI 服务器，用于运行 FastAPI 应用。
- **[Pillow](https://python-pillow.org/)**: Python 图像处理库，用于处理上传的图像。
- **[pydicom](https://pydicom.github.io/)**: 用于解析 DICOM 格式的医疗图像文件。
- **[NumPy](https://numpy.org/)**: Python 的科学计算基础库，用于高效的像素级运算。
- **[python-multipart](https://pypi.org/project/python-multipart/)**: 用于处理 FastAPI 中的文件上传。
