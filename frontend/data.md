# **数据结构与状态管理文档**

本文档旨在详细说明 **CT 肺结节检测系统前端** 应用中所使用的核心数据结构以及基于 **Redux** 的状态管理模型。

---

## **1. 核心数据结构**

应用的数据模型围绕着图像 (`ImageFile`) 和结节 (`Nodule`) 进行设计。

### **1.1. `Nodule` - 结节**

描述在医学图像上检测到的一个结节（或病灶）的信息。

```typescript
interface Nodule {
  id: number;     // 结节的唯一标识符
  x: number;      // 结节边界框左上角的 X 坐标（像素）
  y: number;      // 结节边界框左上角的 Y 坐标（像素）
  width: number;  // 结节边界框的宽度（像素）
  height: number; // 结节边界框的高度（像素）
}
```

### **1.2. `ImageFile` - 图像文件**

代表一个用户上传的图像文件及其相关状态。

```typescript
interface ImageFile {
  id: string;         // 基于时间戳和文件名生成的唯一 ID
  file: File;         // 浏览器原生的 File 对象
  imageUrl: string;   // 图像的访问 URL。对于 DICOM，是 Cornerstone 的 imageId；对于其他格式，是 Object URL
  nodules: Nodule[];  // 与此图像关联的结节列表
  isDicom: boolean;   // 标记此文件是否为 DICOM 格式
}
```

---

## **2. Redux 状态管理 (`AppState`)**

应用使用 Redux 来管理全局状态，确保数据流的一致性和可预测性。根状态 (`AppState`) 的结构如下：

### **2.1. `AppState` 结构**

```typescript
interface AppState {
  images: ImageFile[];          // 存储所有上传的图像对象
  activeImageId: string | null; // 当前正在查看和操作的图像的 ID
  ww: number;                   // 全局窗宽 (Window Width)，用于调整图像对比度
  wl: number;                   // 全局窗位 (Window Level)，用于调整图像亮度
  selectedNodule: Nodule | null;// 当前选中的结节对象，用于高亮和局部放大
  showNodules: boolean;         // 控制是否在图像上显示所有结节的标注框
}
```

---

## **3. Redux Actions**

Actions 是触发状态更新的唯一方式。以下是本应用定义的核心 Actions。

| Action 类型 (`type`) | 描述 | `payload` 数据 | 触发时机 |
| :--- | :--- | :--- | :--- |
| `ADD_IMAGES` | 添加一个或多个新的图像文件到 `images` 列表。 | `ImageFile[]` | 用户通过 `ImageUploader` 组件上传文件后。 |
| `SET_ACTIVE_IMAGE` | 设置当前活动的图像。 | `string \| null` | 用户在 `ThumbnailList` 组件中点击一个缩略图时。 |
| `SET_NODULES_FOR_IMAGE` | 为指定的图像更新其结节列表。 | `{ imageId: string, nodules: Nodule[] }` | `detectNodules` 异步 action 成功从后端获取到数据后。 |
| `SET_WW` | 更新全局的窗宽值。 | `number` | 用户在 `WindowAdjuster` 组件中拖动窗宽滑块时。 |
| `SET_WL` | 更新全局的窗位值。 | `number` | 用户在 `WindowAdjuster` 组件中拖动窗位滑块时。 |
| `SELECT_NODULE` | 设置当前选中的结节。 | `Nodule \| null` | 用户在 `NoduleList` 组件中点击一个结节项时。 |
| `SET_SHOW_NODULES` | 控制结节标注的显示或隐藏。 | `boolean` | `detectNodules` 成功后自动设为 `true`，未来可添加手动开关。 |

### **3.1. 异步 Actions (Thunks)**

-   **`uploadImages(files: File[])`**
    -   **功能**: 接收 `File` 对象数组，将它们转换为 `ImageFile` 结构，并分发 `ADD_IMAGES` action。
    -   **处理**: 会判断文件是否为 DICOM 格式，并相应地生成 `imageUrl`。

-   **`detectNodules()`**
    -   **功能**: 这是核心的业务 action。它获取当前活动图像，通过 `axios` 将其发送到后端 API (`/api/detect-nodules`)。
    -   **处理**: 成功后，它会分发 `SET_NODULES_FOR_IMAGE` action 来更新结节数据，并分发 `SET_SHOW_NODULES` action 来确保标注可见。

-   **`adjustWindow(ww: number, wl: number)`**
    -   **功能**: 接收新的窗宽和窗位值。
    -   **处理**: 分发 `SET_WW` 和 `SET_WL` actions 来更新状态。