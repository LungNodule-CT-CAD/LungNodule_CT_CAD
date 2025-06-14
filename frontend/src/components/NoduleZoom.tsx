import React, { useRef, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '@store/index';

/**
 * 结节放大显示组件
 * TODO: 此组件需要使用 Cornerstone 的 MagnifyTool 进行重构。
 * 当前实现已不兼容，暂时禁用以防出错。
 */
const NoduleZoom: React.FC = () => {
  const { selectedNodule } = useSelector((state: RootState) => state);
//   const canvasRef = useRef<HTMLCanvasElement>(null);

  // 原始逻辑依赖于 `uploadedImage` 和手动 canvas 绘制，已不适用
  // useEffect(() => { ... });

  if (!selectedNodule) {
    return <p className="zoom-prompt" style={{color: '#888', fontSize: '0.8rem'}}>选择一个结节以查看放大图像</p>;
  }

  return (
    <div className="zoom-container">
      {/* <h4>结节放大镜</h4> */}
      <p style={{color: '#888', fontSize: '0.8rem'}}>放大镜功能待实现</p>
      {/* <canvas
        ref={canvasRef}
        className="zoom-canvas"
      ></canvas> */}
    </div>
  );
};

export default NoduleZoom;
