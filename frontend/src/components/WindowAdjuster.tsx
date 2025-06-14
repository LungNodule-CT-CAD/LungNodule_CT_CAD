import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@store/index';
import cornerstone from 'cornerstone-core';
import { adjustWindow } from '@store/actions';

/**
 * 窗宽窗位调整组件
 * TODO: 此组件需要重构以适配Cornerstone的交互方式。
 * 当前已通过鼠标直接在图像上调整，此滑块功能暂时禁用。
 */
const WindowAdjuster: React.FC = () => {
  const { ww: initialWw, wl: initialWl, activeImageId } = useSelector((state: RootState) => state);
  const dispatch: AppDispatch = useDispatch();

  const [ww, setWw] = useState(initialWw);
  const [wl, setWl] = useState(initialWl);

  // 默认值
  const DEFAULT_WW = 1500;
  const DEFAULT_WL = -600;

  useEffect(() => {
    setWw(initialWw);
    setWl(initialWl);
  }, [initialWw, initialWl]);

  // 滑块变更时实时调整影像窗宽/窗位
  const updateViewport = (newWw: number, newWl: number) => {
    const element = document.querySelector('.image-viewer') as HTMLElement | null;
    if (element) {
      try {
        const viewport = cornerstone.getViewport(element);
        if (viewport) {
          viewport.voi.windowWidth = newWw;
          viewport.voi.windowCenter = newWl;
          cornerstone.setViewport(element, viewport);
        }
      } catch (e) {}
    }
  };

  const handleWwChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    setWw(value);
    updateViewport(value, wl);
  };

  const handleWlChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    setWl(value);
    updateViewport(ww, value);
  };

  const handleMouseUp = () => {
    if (activeImageId) {
      dispatch(adjustWindow(ww, wl));
    }
  };

  // 重置窗宽
  const handleResetWw = () => {
    setWw(DEFAULT_WW);
    updateViewport(DEFAULT_WW, wl);
    dispatch(adjustWindow(DEFAULT_WW, wl));
  };
  // 重置窗位
  const handleResetWl = () => {
    setWl(DEFAULT_WL);
    updateViewport(ww, DEFAULT_WL);
    dispatch(adjustWindow(ww, DEFAULT_WL));
  };
  
  const isDisabled = !activeImageId;

  return (
    <div className="window-adjuster">
      <div className="slider-container">
        <button onClick={handleResetWw} style={{marginRight: 6, fontSize: '0.9em', padding: '2px 8px'}}>重置</button>
        <label htmlFor="ww-slider">窗宽 (WW): <span style={{color:'#64ffda', fontWeight:600}}>{ww}</span></label>
        <input
          id="ww-slider"
          type="range"
          min="1"
          max="4096"
          value={ww}
          onChange={handleWwChange}
          onMouseUp={handleMouseUp}
          className="slider"
          disabled={isDisabled}
        />
      </div>
      <div className="slider-container">
        <button onClick={handleResetWl} style={{marginRight: 6, fontSize: '0.9em', padding: '2px 8px'}}>重置</button>
        <label htmlFor="wl-slider">窗位 (WL): <span style={{color:'#64ffda', fontWeight:600}}>{wl}</span></label>
        <input
          id="wl-slider"
          type="range"
          min="-2000"
          max="2000"
          value={wl}
          onChange={handleWlChange}
          onMouseUp={handleMouseUp}
          className="slider"
          disabled={isDisabled}
        />
      </div>
      {isDisabled && (
         <div className="disabled-text" style={{textAlign: 'center', fontSize: '0.8rem', color: '#888', marginTop: '8px'}}>
            <p>选择图像后可调整</p>
         </div>
      )}
    </div>
  );
};

export default WindowAdjuster;
