# **CT 肺结节检测系统 - 后端 API 文档**

## **1. 概述**
本文档为 CT 肺结节检测系统前端项目提供后端 API 规范。前端应用需要以下三个核心接口来支持其功能。为了方便测试，你可以构建一个简易的后端服务来实现这些接口。

- **基础 URL**: 所有 API 路由都基于服务器根路径，例如 `http://localhost:5000`。
- **数据格式**: 所有请求和响应的主体都应为 `JSON` 格式，文件上传除外。

---

## **2. API 接口详解**

### **2.1 图像上传接口**

- **功能**:接收用户上传的 CT 图像文件，进行初步处理或存储，并返回可供前端显示的图像数据。
- **URL**: `/api/upload`
- **方法**: `POST`
- **请求头**:
  - `Content-Type`: `multipart/form-data`
- **请求体 (Form Data)**:
  - `file`: (File) 用户上传的图像文件。

- **成功响应 (200 OK)**:
  - **响应体 (JSON)**:
    ```json
    {
      "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..." 
    }
    ```
    - `image`: 返回处理后的图像数据，推荐使用 Base64 编码的字符串，以便前端直接在 `<img>` 或 `<canvas>` 中使用。

- **测试建议**: 后端收到文件后，可以将其转换为 PNG 或 JPEG 格式，然后编码为 Base64 字符串返回。

---

### **2.2 调整窗宽窗位接口**

- **功能**: 根据前端传递的窗宽（WW）和窗位（WL）参数，调整图像的显示效果。
- **URL**: `/api/adjust-window`
- **方法**: `POST`
- **请求头**:
  - `Content-Type`: `application/json`
- **请求体 (JSON)**:
  ```json
  {
    "ww": 1500,
    "wl": -600,
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
  }
  ```
  - `ww`: (number) 新的窗宽值。
  - `wl`: (number) 新的窗位值。
  - `image`: (string) 当前正在操作的图像的 Base64 数据。

- **成功响应 (200 OK)**:
  - **响应体 (JSON)**:
    ```json
    {
      "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
    }
    ```
    - `image`: 返回应用了新窗宽/窗位参数后的图像 Base64 数据。

- **测试建议**: 后端可以忽略传入的 `image` 数据，仅返回一张预设的、经过不同效果处理的图片 Base64，以模拟调整功能。

---

### **2.3 肺结节检测接口**

- **功能**: 对指定的图像进行分析，找出其中包含的肺结节，并返回它们的坐标信息。
- **URL**: `/api/detect-nodules`
- **方法**: `POST`
- **请求头**:
  - `Content-Type`: `application/json`
- **请求体 (JSON)**:
  ```json
  {
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
  }
  ```
  - `image`: (string) 需要进行结节检测的图像的 Base64 数据。

- **成功响应 (200 OK)**:
  - **响应体 (JSON)**:
    ```json
    {
      "nodules": [
        { "id": 1, "x": 150, "y": 200, "width": 20, "height": 20 },
        { "id": 2, "x": 250, "y": 300, "width": 25, "height": 25 },
        { "id": 3, "x": 350, "y": 150, "width": 15, "height": 15 }
      ]
    }
    ```
    - `nodules`: (Array) 一个包含多个结节对象的数组。
      - `id`: (number) 结节的唯一标识符。
      - `x`: (number) 结节标注框左上角的 X 坐标。
      - `y`: (number) 结节标注框左上角的 Y 坐标。
      - `width`: (number) 标注框的宽度。
      - `height`: (number) 标注框的高度。

- **测试建议**: 这是测试的核心。后端收到请求后，**无需进行真实的模型推理**。只需**随机生成** 2 到 5 个结节对象，其 `x`, `y`, `width`, `height` 在合理的图像范围内随机取值，然后将这个数组返回即可。这可以非常方便地模拟出检测到不同数量和位置的结节的场景。 