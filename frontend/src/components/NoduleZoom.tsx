import React, { useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '@store/index';

/**
 * 结节放大显示组件
 * - 监听选中的结节（selectedNodule）和上传的图像。
 * - 当有结节被选中时，将其对应区域从原图中裁剪并放大显示。
 */
const NoduleZoom: React.FC = () => {
  // 从Redux store中获取所需的状态
  const { uploadedImage, selectedNodule } = useSelector((state: RootState) => state);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const zoomFactor = 4; // 放大倍数

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    // 如果有选中的结节和图像，则执行放大逻辑
    if (selectedNodule && uploadedImage) {
      const image = new Image();
      image.src = uploadedImage;
      image.onload = () => {
        // 清空画布
        context.clearRect(0, 0, canvas.width, canvas.height);

        // 定义裁剪区域的源坐标和尺寸
        const sx = selectedNodule.x;
        const sy = selectedNodule.y;
        const sWidth = selectedNodule.width;
        const sHeight = selectedNodule.height;

        // 定义在目标画布上绘制的坐标和尺寸（放大效果）
        const dx = 0;
        const dy = 0;
        const dWidth = sWidth * zoomFactor;
        const dHeight = sHeight * zoomFactor;

        // 设置画布尺寸以适应放大后的图像
        canvas.width = dWidth;
        canvas.height = dHeight;

        // 从原图中裁剪并放大绘制到当前画布上
        context.drawImage(image, sx, sy, sWidth, sHeight, dx, dy, dWidth, dHeight);
      };
    } else {
      // 如果没有选中的结节，则清空画布
      context.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, [selectedNodule, uploadedImage]); // 依赖项：当选中结节或图像变化时更新

  // 如果没有选中结节，则显示提示信息
  if (!selectedNodule) {
    return <p className="zoom-prompt">请在列表中选择一个结节以查看放大图像</p>;
  }

  return (
    <div className="zoom-container">
      <h4>结节放大镜</h4>
      <canvas
        ref={canvasRef}
        className="zoom-canvas"
      ></canvas>
    </div>
  );
};

export default NoduleZoom;
