# CT肺结节检测系统 - 数据格式文档

本文件详细说明前端内部使用的核心数据结构，便于团队成员理解和开发。关于前后端接口的详细规范，请参考 `api.md`。

---

## 1. 前端全局状态（AppState）数据结构

前端使用 Redux 集中管理应用状态，以支持多图像上传和独立分析。核心结构如下：

```typescript
// 定义单个结节的数据结构
interface Nodule {
  id: number;     // 结节唯一ID
  x: number;      // 左上角X坐标
  y: number;      // 左上角Y坐标
  width: number;  // 宽度
  height: number; // 高度
}

// 定义单个上传图像文件的数据结构
interface ImageFile {
  id: string;          // 基于时间戳和文件名的唯一ID
  file: File;          // 原始文件对象，用于发送到后端
  imageUrl: string;    // 在客户端生成的Base64或Object URL，用于本地预览
  nodules: Nodule[];   // 与此图像关联的结节列表
}

// 定义应用的主状态树
interface AppState {
  images: ImageFile[];          // 所有已上传图像的列表
  activeImageId: string | null; // 当前被选中用于显示和分析的图像ID
  ww: number;                   // 图像显示的窗宽（全局设置）
  wl: number;                   // 图像显示的窗位（全局设置）
  selectedNodule: Nodule | null;// 在活动图像上选中的结节
  showNodules: boolean;         // 是否在活动图像上显示结节标注
}
```

---

## 2. 典型数据流示例

新的工作流程支持多图像处理：

1.  **用户上传一张或多张图像**:
    - 前端 `ImageUploader` 组件接收文件。
    - `uploadImages` action 被调用。
    - 前端使用 `FileReader` 将每个文件转换为 Base64 `imageUrl` 用于本地预览。
    - 为每个文件创建一个 `ImageFile` 对象（包含唯一 `id`, `File` 对象, `imageUrl` 和一个空的 `nodules` 数组）。
    - 这些 `ImageFile` 对象被添加到 Redux store 的 `images` 数组中。
    - 默认第一张上传的图片被设为活动图片（`activeImageId` 被设置）。

2.  **用户点击缩略图切换图像**:
    - `ThumbnailList` 组件捕获点击事件。
    - `setActiveImage` action 被调用，并传入被点击图像的 `id`。
    - Redux store 更新 `activeImageId`。
    - `ImageViewer` 和 `NoduleList` 组件监听到 `activeImageId` 的变化，并重新渲染以显示新活动图像及其关联的结节。

3.  **用户对当前活动图像发起结节检测**:
    - 用户点击"开始预测"按钮。
    - `detectNodules` action 被调用。
    - 该 action 从 Redux store 中找到 `activeImageId` 对应的 `ImageFile` 对象。
    - 从该对象中提取原始的 `File` 对象 (`imageFile.file`)。
    - 将此文件通过 `FormData` 发送到后端的 `/api/detect-nodules` 接口。
    - 后端返回检测到的 `nodules` 数组。
    - 前端调用 `setNodulesForImage` action，将返回的结节列表更新到 `activeImageId` 对应的那个 `ImageFile` 对象的 `nodules` 字段中。

---

## 3. 约定与注意事项
- 前后端接口的请求和响应格式，请严格遵循 `api.md` 文档。
- 结节坐标和尺寸均为像素单位，基于图像的原始分辨率。
- 所有与特定图像相关的数据（如结节列表）都存储在各自的 `ImageFile` 对象中，实现了数据隔离。

---

如需扩展数据结构，请在本文件补充说明，并同步更新前端 `src/store/types.ts`。 