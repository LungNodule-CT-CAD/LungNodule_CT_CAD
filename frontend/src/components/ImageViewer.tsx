import React, { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
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
const ImageViewer = forwardRef<{ reset: () => void }, {}>((props, ref) => {
  const { images, activeImageId, selectedNodule, showNodules } = useSelector((state: RootState) => state);
  const elementRef = useRef<HTMLDivElement>(null);
  const contourCanvasRef = useRef<HTMLCanvasElement>(null);

  const activeImage = images.find(img => img.id === activeImageId);

  // cornerstone 启用/禁用
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
        } catch(error) {}
      }
    };
  }, []);

  // cornerstone 加载并显示图像
  useEffect(() => {
    const element = elementRef.current;
    if (element && activeImage) {
        cornerstone.loadImage(activeImage.imageUrl).then(image => {
            const viewport = cornerstone.getDefaultViewportForImage(element, image);
            cornerstone.displayImage(element, image, viewport);
            // 注册并激活 PanTool
            try { cornerstoneTools.addTool(cornerstoneTools.PanTool); } catch (_) {}
            cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 1 });
        }).catch(error => {
            console.error("Cornerstone Image Load Failed:", error);
        });
    }
  }, [activeImage]);

  // 滚轮缩放
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      try {
        const viewport = cornerstone.getViewport(element);
        if (!viewport) return;
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

  // 轮廓canvas尺寸同步
  useEffect(() => {
    const element = elementRef.current;
    const canvas = contourCanvasRef.current;
    if (!element || !canvas) return;
    const resize = () => {
      const rect = element.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [activeImage]);

  // 监听 cornerstone 渲染事件，canvas 尺寸和内容自适应 cornerstone 图像
  useEffect(() => {
    const element = elementRef.current;
    const canvas = contourCanvasRef.current;
    if (!element || !canvas) return;

    function drawContours() {
      if (!element || !canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      // 同步canvas尺寸到cornerstone显示区域
      const rect = element.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!showNodules || !activeImage || !activeImage.nodules || activeImage.nodules.length === 0) return;
      const enabledElement = cornerstone.getEnabledElement(element);
      const viewport = enabledElement.viewport;
      const image = enabledElement.image;
      if (!viewport || !image) return;
      activeImage.nodules.forEach(nodule => {
        const points = nodule.contour;
        if (!points || points.length < 2) return;
        ctx.beginPath();
        const first = cornerstone.pixelToCanvas(element as HTMLElement, points[0] as any);
        ctx.moveTo(first.x, first.y);
        for (let i = 1; i < points.length; i++) {
          const pt = cornerstone.pixelToCanvas(element as HTMLElement, points[i] as any);
          ctx.lineTo(pt.x, pt.y);
        }
        ctx.closePath();
        if (selectedNodule && selectedNodule.id === nodule.id) {
          ctx.lineWidth = 4;
          ctx.strokeStyle = '#00ffe7';
        } else {
          ctx.lineWidth = 2;
          ctx.strokeStyle = 'rgba(255,255,0,0.7)';
        }
        ctx.stroke();
      });
    }
    element.addEventListener('cornerstoneimagerendered', drawContours);
    // 首次主动绘制一次
    drawContours();
    return () => {
      element.removeEventListener('cornerstoneimagerendered', drawContours);
    };
  }, [activeImage, showNodules, selectedNodule]);

  // 复位函数
  const handleReset = () => {
    const element = elementRef.current;
    if (element && activeImage) {
      cornerstone.loadImage(activeImage.imageUrl).then(image => {
        const viewport = cornerstone.getDefaultViewportForImage(element, image);
        cornerstone.setViewport(element, viewport);
      });
    }
  };

  useImperativeHandle(ref, () => ({
    reset: handleReset
  }));

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div 
        ref={elementRef} 
        className="image-viewer"
        style={{ width: '100%', height: '100%', zIndex: 0 }}
        onContextMenu={(e) => e.preventDefault()}
      >
        {activeImage && (
          <img
            src={activeImage.imageUrl}
            alt="CT图像"
            loading="lazy"
            style={{ maxWidth: '100%', maxHeight: '600px', objectFit: 'contain' }}
          />
        )}
      </div>
      <canvas
        ref={contourCanvasRef}
        style={{ position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}
      />
      {!activeImage && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#ccc' }}>
          <p>请先上传并选择一张图像</p>
        </div>
      )}
    </div>
  );
});

export default ImageViewer;
