# CT肺结节检测系统 - 数据格式文档

本文件详细说明前后端交互及前端内部使用的所有核心数据结构，便于团队成员理解和开发。

---

## 1. 图像上传接口数据格式

### 1.1 请求（前端 → 后端）
- **URL**: `/api/upload`
- **方法**: `POST`
- **请求头**: `Content-Type: multipart/form-data`
- **请求体**:
  - `file`: (File) 用户上传的CT图像文件（DICOM格式，扩展名`.dcm`或`.dicom`）。

### 1.2 响应（后端 → 前端）
- **响应体 (JSON)**:
```json
{
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```
- 字段说明：
  - `image` (string): 处理后的图像数据，Base64编码字符串，前端可直接用于`<img>`或`<canvas>`。

---

## 2. 窗宽/窗位调整接口数据格式

### 2.1 请求（前端 → 后端）
- **URL**: `/api/adjust-window`
- **方法**: `POST`
- **请求头**: `Content-Type: application/json`
- **请求体**:
```json
{
  "ww": 1500,
  "wl": -600,
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```
- 字段说明：
  - `ww` (number): 新的窗宽（Window Width）值。
  - `wl` (number): 新的窗位（Window Level）值。
  - `image` (string): 当前操作的图像Base64数据。

### 2.2 响应（后端 → 前端）
- **响应体 (JSON)**:
```json
{
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```
- 字段说明：
  - `image` (string): 应用新窗宽/窗位参数后的图像Base64数据。

---

## 3. 肺结节检测接口数据格式

### 3.1 请求（前端 → 后端）
- **URL**: `/api/detect-nodules`
- **方法**: `POST`
- **请求头**: `Content-Type: application/json`
- **请求体**:
```json
{
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
}
```
- 字段说明：
  - `image` (string): 需要检测的图像Base64数据。

### 3.2 响应（后端 → 前端）
- **响应体 (JSON)**:
```json
{
  "nodules": [
    { "id": 1, "x": 150, "y": 200, "width": 20, "height": 20 },
    { "id": 2, "x": 250, "y": 300, "width": 25, "height": 25 }
  ]
}
```
- 字段说明：
  - `nodules` (array): 结节对象数组，每个对象结构如下：
    - `id` (number): 结节唯一标识符。
    - `x` (number): 结节标注框左上角X坐标（像素）。
    - `y` (number): 结节标注框左上角Y坐标（像素）。
    - `width` (number): 标注框宽度（像素）。
    - `height` (number): 标注框高度（像素）。

---

## 4. 前端全局状态（AppState）数据结构

前端使用Redux集中管理应用状态，核心结构如下：

```typescript
interface AppState {
  uploadedImage: string | null;  // 已上传的医学影像（Base64或URL）
  ww: number;                   // 当前窗宽
  wl: number;                   // 当前窗位
  nodules: Nodule[];            // 检测到的结节列表
  selectedNodule: Nodule | null;// 当前选中的结节
}

interface Nodule {
  id: number;     // 结节唯一ID
  x: number;      // 左上角X坐标
  y: number;      // 左上角Y坐标
  width: number;  // 宽度
  height: number; // 高度
}
```

---

## 5. 典型数据流示例

1. **用户上传DICOM文件** → `/api/upload` → 返回Base64图像 → 存入`uploadedImage`。
2. **用户调整窗宽/窗位** → `/api/adjust-window` → 返回新Base64图像 → 更新`uploadedImage`。
3. **用户发起结节检测** → `/api/detect-nodules` → 返回`nodules`数组 → 存入`nodules`。

---

## 6. 约定与注意事项
- 所有图像数据均采用Base64字符串传递，前缀格式为`data:image/png;base64,`。
- 结节坐标和尺寸均为像素单位，基于返回图像的原始分辨率。
- 前端所有状态字段和后端接口字段需严格保持一致，避免类型不匹配。

---

如需扩展数据结构，请在本文件补充说明，并同步更新前端`src/store/types.ts`和后端接口文档。 