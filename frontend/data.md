# **前端核心数据结构说明（2024升级版）**

本文件详细说明了前端各核心数据结构，已适配"结节轮廓点集+canvas绘制"方案。

---

## 1. 结节结构 Nodule

```ts
export interface Nodule {
  id: number; // 结节唯一标识
  contour: Array<{ x: number; y: number }>; // 结节真实轮廓点集
}
```
- `contour` 是一个点集数组，数组内每个元素为 `{x, y}`，表示该结节的真实边界。
- 轮廓点集为像素坐标，直接对应原始图像。

---

## 2. 图像文件结构 ImageFile

```ts
export interface ImageFile {
  id: string; // 唯一ID
  file: File;
  imageUrl: string; // cornerstone的imageId或Object URL
  nodules: Nodule[]; // 检测到的所有结节
  isDicom: boolean; // 是否为DICOM
}
```

---

## 3. 全局状态结构 AppState

```ts
export interface AppState {
  images: ImageFile[];
  activeImageId: string | null;
  ww: number; // 窗宽
  wl: number; // 窗位
  selectedNodule: Nodule | null; // 当前高亮结节
  showNodules: boolean; // 是否显示结节轮廓
}
```

---

## 4. 交互与渲染说明
- 前端所有结节标注均通过 canvas 绘制，不再依赖 cornerstone-tools 标注系统。
- 主图像区采用双canvas分层渲染，底层为医学影像，顶层canvas绘制所有结节轮廓。
- 轮廓高亮、缩放、平移、切换等交互全部实时同步。
- 局部放大区同样基于 contour 点集绘制。

---

## 5. 典型数据示例

```json
{
  "id": 1,
  "contour": [
    { "x": 100, "y": 120 },
    { "x": 102, "y": 121 },
    { "x": 105, "y": 123 }
    // ...
  ]
}
```

---

## **Redux Actions**

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