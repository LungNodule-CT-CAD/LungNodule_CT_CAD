import React, { useEffect, useRef } from 'react';
import { useSelector } from 'react-redux';
import cornerstone from 'cornerstone-core';
import { RootState } from '@store/index';

/**
 * 结节局部放大组件
 * - 放大显示当前选中结节周围区域
 * - 随 selectedNodule 变化自动刷新
 */
const ZOOM_SIZE = 110; // 放大区域原图像素（原64，适当增大，提升细节）
const CANVAS_SIZE = 220; // 展示canvas大小（原128，现220）

const NoduleLocalZoom: React.FC = () => {
  const { images, activeImageId, selectedNodule } = useSelector((state: RootState) => state);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const activeImage = images.find(img => img.id === activeImageId);

  useEffect(() => {
    const drawZoom = async () => {
      if (!activeImage || !selectedNodule || !canvasRef.current) return;
      try {
        const image = await cornerstone.loadImage(activeImage.imageUrl);
        const ctx = canvasRef.current.getContext('2d');
        if (!ctx) return;
        // 计算结节中心
        const cx = selectedNodule.x + selectedNodule.width / 2;
        const cy = selectedNodule.y + selectedNodule.height / 2;
        // 截取区域左上角
        const sx = Math.max(0, Math.round(cx - ZOOM_SIZE / 2));
        const sy = Math.max(0, Math.round(cy - ZOOM_SIZE / 2));
        // 获取原始像素数据
        const pixelData = image.getPixelData();
        const { width, height } = image;
        // 创建灰度ImageData
        const zoomImage = ctx.createImageData(ZOOM_SIZE, ZOOM_SIZE);
        for (let y = 0; y < ZOOM_SIZE; y++) {
          for (let x = 0; x < ZOOM_SIZE; x++) {
            const srcX = sx + x;
            const srcY = sy + y;
            if (srcX < 0 || srcX >= width || srcY < 0 || srcY >= height) continue;
            const srcIdx = srcY * width + srcX;
            const val = pixelData[srcIdx];
            const idx = (y * ZOOM_SIZE + x) * 4;
            zoomImage.data[idx] = val;
            zoomImage.data[idx + 1] = val;
            zoomImage.data[idx + 2] = val;
            zoomImage.data[idx + 3] = 255;
          }
        }
        ctx.putImageData(zoomImage, 0, 0);
        // 放大显示
        const temp = ctx.getImageData(0, 0, ZOOM_SIZE, ZOOM_SIZE);
        ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
        ctx.imageSmoothingEnabled = false;
        ctx.putImageData(temp, 0, 0);
        ctx.drawImage(canvasRef.current, 0, 0, ZOOM_SIZE, ZOOM_SIZE, 0, 0, CANVAS_SIZE, CANVAS_SIZE);
      } catch (e) {}
    };
    drawZoom();
  }, [activeImage, selectedNodule]);

  if (!selectedNodule) {
    return <div style={{color:'#888', fontSize:'1rem', textAlign:'center', minHeight:CANVAS_SIZE, display:'flex', alignItems:'center', justifyContent:'center'}}>请选择结节以放大</div>;
  }

  return (
    <div style={{display:'flex', flexDirection:'column', alignItems:'center', width: '100%', height: '100%', justifyContent: 'space-around'}}>
      <div style={{fontSize:'1rem', color:'#64ffda', marginTop:8, fontWeight:600, alignSelf:'flex-start', paddingLeft:12}}>结节局部放大</div>
      <canvas ref={canvasRef} width={CANVAS_SIZE} height={CANVAS_SIZE} style={{border:'2px solid #1c2a4a', borderRadius:12, background:'#222', boxShadow:'0 2px 12px #0006'}} />
      <div style={{alignSelf:'stretch', padding:'0 12px'}}>
        <h4 style={{fontSize:'0.9rem', color:'#64ffda', marginBottom:8, borderBottom:'1px solid #1c2a4a', paddingBottom:4}}>结节信息</h4>
        <div style={{fontSize:'0.85rem', color:'#ccc', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'4px 12px'}}>
          <span>X: <b style={{color:'white'}}>{selectedNodule.x}</b></span>
          <span>Y: <b style={{color:'white'}}>{selectedNodule.y}</b></span>
          <span>宽: <b style={{color:'white'}}>{selectedNodule.width}</b></span>
          <span>高: <b style={{color:'white'}}>{selectedNodule.height}</b></span>
        </div>
      </div>
    </div>
  );
};

export default NoduleLocalZoom; 