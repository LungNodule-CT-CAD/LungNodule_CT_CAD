### 前端修改指南：从矩形标注升级到轮廓标注

**目标：** 将前端的结节标注从显示"外接矩形"升级为显示更精确的"结节轮廓"。

**1. API响应数据结构变化**

首先，前端需要了解，后端 `/api/predict` 接口的返回数据格式已经改变。

*   **旧格式 (矩形):**
    ```json
    [
      {
        "id": 1,
        "x": 100,
        "y": 120,
        "width": 25,
        "height": 30
      }
    ]
    ```

*   **新格式 (轮廓):**
    ```json
    [
      {
        "id": 1,
        "contour": [
          { "x": 100, "y": 120 },
          { "x": 102, "y": 121 },
          { "x": 105, "y": 123 },
          ... 
        ]
      }
    ]
    ```
    每个结节对象现在包含一个 `contour` 字段，它是一个数组，数组里是组成该结节轮廓的所有点的 `x, y` 坐标对象。

**2. 前端修改建议**

你的前端似乎是基于 `React` 和 `Cornerstone.js` 构建的。`Cornerstone.js` 提供了强大的医学影像工具，非常适合用来绘制轮廓。

**修改步骤概览：**

1.  **更新数据获取逻辑：** 在你前端代码中获取并处理API返回结果的地方，你需要修改数据模型（state），使其能够存储新的轮廓数据结构。

2.  **修改或创建新的渲染工具：** 在 `Cornerstone.js` 中，你需要一个工具来绘制多边形（Polygon）。你可能正在使用 `cornerstone-tools` 库。
    *   检查你正在使用的 `cornerstone-tools` 版本。较新的版本（v4以上）有更灵活的工具自定义方式。
    *   你可以寻找一个现有的 `Polygon` 或 `Freehand` 绘图工具，并改造它来显示后端传来的数据，而不是让用户手动绘制。

3.  **渲染轮廓的核心逻辑：**
    *   当用户上传图片并成功获取到后端的轮廓数据后，遍历返回的结节列表。
    *   对于每一个结节的 `contour` 数组，调用 `Cornerstone.js` 的绘图API，在图像上绘制一个多边形。你需要将 `contour` 数组中的点坐标，转换成 `Cornerstone` 绘图工具所需要的数据格式。
    *   通常，绘图工具会有一个 `toolState` 或类似的状态管理器。你需要以编程方式将你的轮廓数据添加到这个 `toolState` 中，`Cornerstone` 就会自动帮你把它渲染到画布上。

**代码示例 (伪代码):**

假设你有一个 `cornerstone-tool` 叫做 `FreehandRoiTool`，下面的伪代码展示了如何以编程方式添加一个轮廓：

```javascript
// 导入工具库
import cornerstoneTools from 'cornerstone-tools';

// 假设这是你从后端获取到的单个结节的轮廓数据
const contourData = [
  { x: 100, y: 120 },
  { x: 102, y: 121 },
  { x: 105, y: 123 },
  // ... more points
];

// 获取图像所在的DOM元素
const element = document.getElementById('cornerstone-image-element');

// cornerstone-tools 工具名称
const toolName = 'FreehandRoi'; 

// 以编程方式添加一个工具状态
// 这会告诉 cornerstone 在图像上绘制这个轮廓
cornerstoneTools.addToolState(element, toolName, {
  data: [{
    visible: true,
    active: false,
    handles: {
      points: contourData // 将你的轮廓点数组传递给工具
    }
  }]
});

// 最后，更新一下图像让它重绘
cornerstone.updateImage(element);
```
**请注意:** 上述代码是示例性的。你需要根据你项目中实际使用的 `cornerstone-tools` 版本和具体的工具名称 (`FreehandRoiTool`, `PolygonRoiTool` 等) 进行调整。关键的函数是 `cornerstoneTools.addToolState()`。

**3. 用户交互**

当用户点击右侧"结节列表"中的某一项时，你可能需要高亮显示对应的轮廓，或者放大到那个区域。你可以通过修改对应轮廓在 `toolState` 中的属性（如 `active: true` 或改变其颜色）来实现这些交互。 