# **CT 肺结节检测系统 - 后端模拟 API**

## **1. 项目概述**

本项目是一个基于 **FastAPI** 构建的后端模拟 (Mock) API 服务器，专为 `CT 肺结节检测系统` 的前端开发提供支持。它模拟了核心的后端功能，使前端团队可以独立进行开发和测试，而无需依赖真实的、可能尚在开发中的模型推理服务。

**核心功能**:
-   **模拟结节检测**: 提供一个 `/api/detect-nodules` 接口，接收前端上传的图像文件（支持 DICOM, PNG, JPG 等），并返回一个包含随机生成的模拟肺结节坐标的列表。
-   **CORS 支持**: 内置跨域资源共享 (CORS) 中间件，允许来自前端开发服务器 (如 `http://localhost:3000`) 的请求。
-   **轻量高效**: 使用 FastAPI 构建，启动快速，资源占用少，非常适合本地开发环境。

---

## **2. 环境设置与运行**

在运行此后端服务器之前，请确保您已安装 Python 3.7+。

1.  **克隆或下载项目到本地。**

2.  **创建并激活虚拟环境 (推荐)**:
    在项目根目录下打开终端，运行以下命令：
    ```bash
    # 创建虚拟环境
    python -m venv venv

    # 激活虚拟环境
    # Windows
    .\\venv\\Scripts\\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **安装依赖:**
    确保你的虚拟环境已激活，然后运行以下命令安装所需的 Python 包：
    ```bash
    pip install -r requirements.txt
    ```

4.  **启动开发服务器：**
    在项目根目录下，运行以下命令来启动 FastAPI 服务器：
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    -   `--reload` 参数会使服务器在代码变更后自动重启，非常适合开发。
    -   `--port 5000` 指定服务器运行在 8000 端口。前端应用的 API 请求地址应配置为 `http://localhost:5000`。

5.  **访问 API 文档**:
    服务器启动后，您可以在浏览器中访问 `http://localhost:5000/docs` 查看由 FastAPI 自动生成的交互式 API 文档 (Swagger UI)。

---

## **3. API 接口**

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
-   **功能**: 模拟肺结节检测。接收一个图像文件，返回随机生成的结节数据。
-   **请求**: `multipart/form-data`，包含一个名为 `file` 的文件字段。
-   **成功响应 (200 OK)**:
    ```json
    {
      "nodules": [
        { "id": 1, "x": 150, "y": 200, "width": 20, "height": 20 },
        { "id": 2, "x": 250, "y": 300, "width": 25, "height": 25 }
      ]
    }
    ```
    -   返回的结节数量为 2 到 5 个，其坐标和尺寸均为在图像范围内随机生成的值。
