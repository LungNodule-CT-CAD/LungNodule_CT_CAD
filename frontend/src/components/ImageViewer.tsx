import React, { useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '@store/index';

/**
 * 图像显示组件
 * - 负责从Redux store中获取上传的图像数据。
 * - 使用HTML5 Canvas将图像渲染到界面上。
 * - 监听图像和结节数据的变化，并动态更新画布。
 */
const ImageViewer: React.FC = () => {
  // 从Redux store中获取uploadedImage, nodules, 和 selectedNodule 状态
  const { uploadedImage, nodules, selectedNodule } = useSelector((state: RootState) => state);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // 获取Canvas的2D渲染上下文
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    if (uploadedImage) {
      // 创建一个新的Image对象来加载上传的图像数据（通常是base64）
      const image = new Image();
      image.src = uploadedImage;
      image.onload = () => {
        // 图像加载完成后，设置canvas尺寸与图像一致
        canvas.width = image.width;
        canvas.height = image.height;
        // 在canvas上绘制图像
        context.drawImage(image, 0, 0);

        // 如果有结节数据，则在图像上绘制结节框
        if (nodules.length > 0) {
          nodules.forEach(nodule => {
            // 根据是否为选中结节，设置不同的颜色和线宽
            const isSelected = selectedNodule?.id === nodule.id;
            context.strokeStyle = isSelected ? 'blue' : 'red'; // 选中用蓝色，未选中用红色
            context.lineWidth = isSelected ? 3 : 2; // 选中的线宽更粗
            context.strokeRect(nodule.x, nodule.y, nodule.width, nodule.height);
          });
        }
      };
    } else {
      // 如果没有上传的图像，则清空画布
      context.clearRect(0, 0, canvas.width, canvas.height);
    }
  }, [uploadedImage, nodules, selectedNodule]); // 添加 selectedNodule 作为依赖项

  return (
    <div>
      {/* 图像渲染的画布 */}
      <canvas
        ref={canvasRef}
        className="image-canvas"
      ></canvas>
      {/* 当没有图像时显示的提示信息 */}
      {!uploadedImage && <p>请先上传一张CT图像</p>}
    </div>
  );
};

export default ImageViewer;
