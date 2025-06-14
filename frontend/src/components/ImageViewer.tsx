import React, { useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '@store/index';
import cornerstone from 'cornerstone-core';
import cornerstoneTools from 'cornerstone-tools';

/**
 * 图像显示组件
 * - 负责从Redux store中获取当前活动的图像数据。
 * - 使用HTML5 Canvas将图像渲染到界面上。
 * - 监听图像和结节数据的变化，并动态更新画布。
 */
const ImageViewer: React.FC = () => {
  const { images, activeImageId, selectedNodule, showNodules } = useSelector((state: RootState) => state);
  const elementRef = useRef<HTMLDivElement>(null);

  const activeImage = images.find(img => img.id === activeImageId);

  // 当组件挂载和卸载时，管理Cornerstone元素的启用/禁用
  useEffect(() => {
    const element = elementRef.current;
    if (element) {
        try {
            cornerstone.getEnabledElement(element);
        } catch (error) {
            cornerstone.enable(element);
        }
    }
    return () => {
      if (element) {
        try {
            cornerstone.getEnabledElement(element);
            cornerstone.disable(element);
        } catch(error) {
            // 元素可能已被禁用或移除，无需操作
        }
      }
    };
  }, []);

  // 加载并显示图像
  useEffect(() => {
    const element = elementRef.current;
    if (element && activeImage) {
        cornerstone.loadImage(activeImage.imageUrl).then(image => {
            const viewport = cornerstone.getDefaultViewportForImage(element, image);
            cornerstone.displayImage(element, image, viewport);
            
            // 1) 全局注册工具（只需一次即可，捕获异常避免重复注册报错）
            try { cornerstoneTools.addTool(cornerstoneTools.PanTool); } catch (_) {}
            try { cornerstoneTools.addTool(cornerstoneTools.ZoomTool, { configuration: { invert: false, preventZoomOutsideImage: false, minScale: 0.1, maxScale: 20.0 }}); } catch (_) {}
            try { cornerstoneTools.addTool(cornerstoneTools.RectangleRoiTool); } catch (_) {}

            // 2) 设置鼠标按钮对应的激活工具
            cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 1 }); // 左键拖拽为平移
            // 滚轮缩放由自定义事件处理
        }).catch(error => {
            console.error("Cornerstone Image Load Failed:", error);
        });
    }
  }, [activeImage]);

  // 滚轮缩放（以鼠标为中心）
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      try {
        const viewport = cornerstone.getViewport(element);
        if (!viewport) return;
        // 计算缩放因子
        const scale = e.deltaY < 0 ? 1.1 : 0.9;
        viewport.scale = (viewport.scale || 1) * scale;
        cornerstone.setViewport(element, viewport);
      } catch (err) {}
    };
    element.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      element.removeEventListener('wheel', handleWheel);
    };
  }, [activeImage]);
  
  // 更新结节标注
  useEffect(() => {
    const element = elementRef.current;
    if (!element || !activeImage) return;

    try {
      cornerstoneTools.clearToolState(element, 'RectangleRoi'); // 总是先清除

      if (showNodules && activeImage.nodules && activeImage.nodules.length > 0) {
        cornerstoneTools.setToolPassive('RectangleRoi'); // 明确设置为被动模式以显示

        activeImage.nodules.forEach(nodule => {
          const measurementData = {
            visible: true,
            active: false,
            color: selectedNodule?.id === nodule.id ? '#64ffda' : 'yellow',
            handles: {
              start: { x: nodule.x, y: nodule.y, highlight: true, active: false },
              end: { x: nodule.x + nodule.width, y: nodule.y + nodule.height, highlight: true, active: false },
              textBox: { active: false, hasMoved: false }
            }
          };
          cornerstoneTools.addToolState(element, 'RectangleRoi', measurementData);
        });
      } else {
        cornerstoneTools.setToolDisabled('RectangleRoi'); // 如果不显示，则明确禁用
      }

      cornerstone.updateImage(element); // 最后统一更新图像

    } catch (error) {
      console.error("Failed to update annotations:", error);
    }
  }, [showNodules, activeImage, selectedNodule]);


  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <div 
            ref={elementRef} 
            className="image-viewer"
            style={{ width: '100%', height: '100%' }}
            // 防止右键菜单
            onContextMenu={(e) => e.preventDefault()}
        >
        </div>
        {!activeImage && (
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#ccc' }}>
                <p>请先上传并选择一张图像</p>
            </div>
        )}
    </div>
  );
};

export default ImageViewer;
