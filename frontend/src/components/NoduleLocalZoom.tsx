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
  const { images, activeImageId, selectedNodule, detectStatus, ww, wl } = useSelector((state: RootState) => state);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const activeImage = images.find(img => img.id === activeImageId);

  useEffect(() => {
    if (detectStatus !== 'detected') return;
    const drawZoom = async () => {
      if (!activeImage || !selectedNodule || !canvasRef.current) return;
      if (!selectedNodule.contour || selectedNodule.contour.length < 2) return;
      try {
        const image = await cornerstone.loadImage(activeImage.imageUrl);
        const ctx = canvasRef.current.getContext('2d');
        if (!ctx) return;
        // 计算轮廓外接矩形
        const xs = selectedNodule.contour.map(p => p.x);
        const ys = selectedNodule.contour.map(p => p.y);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        const cx = (minX + maxX) / 2;
        const cy = (minY + maxY) / 2;
        // 截取区域左上角
        const sx = Math.max(0, Math.round(cx - ZOOM_SIZE / 2));
        const sy = Math.max(0, Math.round(cy - ZOOM_SIZE / 2));
        // 获取原始像素数据
        const pixelData = image.getPixelData();
        const { width, height } = image;
        // 获取DICOM像素属性
        const slope = image.slope !== undefined ? image.slope : 1;
        const intercept = image.intercept !== undefined ? image.intercept : 0;
        // 创建灰度ImageData（应用窗宽窗位LUT）
        const zoomImage = ctx.createImageData(ZOOM_SIZE, ZOOM_SIZE);
        for (let y = 0; y < ZOOM_SIZE; y++) {
          for (let x = 0; x < ZOOM_SIZE; x++) {
            const srcX = sx + x;
            const srcY = sy + y;
            if (srcX < 0 || srcX >= width || srcY < 0 || srcY >= height) continue;
            const srcIdx = srcY * width + srcX;
            let val = pixelData[srcIdx];
            // 应用DICOM rescaleSlope/intercept
            val = val * slope + intercept;
            // 应用窗宽窗位LUT
            let displayVal = 0;
            if (ww > 0) {
              if (val <= wl - 0.5 - (ww - 1) / 2) {
                displayVal = 0;
              } else if (val > wl - 0.5 + (ww - 1) / 2) {
                displayVal = 255;
              } else {
                displayVal = ((val - (wl - 0.5)) / (ww - 1) + 0.5) * 255;
              }
            }
            displayVal = Math.max(0, Math.min(255, displayVal));
            const idx = (y * ZOOM_SIZE + x) * 4;
            zoomImage.data[idx] = displayVal;
            zoomImage.data[idx + 1] = displayVal;
            zoomImage.data[idx + 2] = displayVal;
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
        // 绘制轮廓
        ctx.save();
        ctx.beginPath();
        // 将原图坐标映射到放大canvas
        selectedNodule.contour.forEach((pt, idx) => {
          const px = ((pt.x - sx) / ZOOM_SIZE) * CANVAS_SIZE;
          const py = ((pt.y - sy) / ZOOM_SIZE) * CANVAS_SIZE;
          if (idx === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.closePath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#64ffda';
        ctx.stroke();
        ctx.restore();
      } catch (e) {}
    };
    drawZoom();
  }, [activeImage, selectedNodule, detectStatus, ww, wl]);

  if (detectStatus !== 'detected') {
    return null;
  }

  if (!selectedNodule) {
    return <div style={{color:'#888', fontSize:'1rem', textAlign:'center', minHeight:CANVAS_SIZE, display:'flex', alignItems:'center', justifyContent:'center'}}>请选择结节以放大</div>;
  }

  // 计算外接矩形信息
  let info = null;
  if (selectedNodule.contour && selectedNodule.contour.length > 1) {
    const xs = selectedNodule.contour.map(p => p.x);
    const ys = selectedNodule.contour.map(p => p.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    info = {
      cx: Math.round((minX + maxX) / 2),
      cy: Math.round((minY + maxY) / 2),
      width: Math.round(maxX - minX),
      height: Math.round(maxY - minY)
    };
  }

  return (
    <div style={{display:'flex', flexDirection:'column', alignItems:'center', width: '100%', height: '100%', justifyContent: 'space-around'}}>
      <div style={{fontSize:'1rem', color:'#64ffda', marginTop:8, fontWeight:600, alignSelf:'flex-start', paddingLeft:12}}>结节局部放大</div>
      <canvas ref={canvasRef} width={CANVAS_SIZE} height={CANVAS_SIZE} style={{border:'2px solid #1c2a4a', borderRadius:12, background:'#222', boxShadow:'0 2px 12px #0006'}} />
      <div style={{alignSelf:'stretch', padding:'0 12px'}}>
        <h4 style={{fontSize:'0.9rem', color:'#64ffda', marginBottom:8, borderBottom:'1px solid #1c2a4a', paddingBottom:4}}>结节信息</h4>
        {info ? (
        <div style={{fontSize:'0.85rem', color:'#ccc', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'4px 12px'}}>
          <span>中心X: <b style={{color:'white'}}>{info.cx}</b></span>
          <span>中心Y: <b style={{color:'white'}}>{info.cy}</b></span>
          <span>宽: <b style={{color:'white'}}>{info.width}</b></span>
          <span>高: <b style={{color:'white'}}>{info.height}</b></span>
        </div>
        ) : null}
      </div>
    </div>
  );
};

export default NoduleLocalZoom; 