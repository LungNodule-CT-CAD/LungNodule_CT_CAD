import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@store/index';
import { adjustWindow } from '@store/actions';

/**
 * 窗宽窗位调整组件
 * - 提供两个滑块，用于调整窗宽（WW）和窗位（WL）。
 * - 从Redux store中读取当前的ww和wl值。
 * - 当用户调整滑块时，更新本地状态以实时显示数值。
 * - 当用户释放滑块时，dispatch 'adjustWindow' action来更新图像。
 */
const WindowAdjuster: React.FC = () => {
  // 从Redux store中获取初始的ww和wl值
  const { ww: initialWw, wl: initialWl, uploadedImage } = useSelector((state: RootState) => state);
  const dispatch: AppDispatch = useDispatch();

  // 使用本地state来控制滑块的实时值，避免频繁更新Redux store
  const [ww, setWw] = useState(initialWw);
  const [wl, setWl] = useState(initialWl);

  // 当store中的初始值变化时（例如，上传新图片后），同步更新本地state
  useEffect(() => {
    setWw(initialWw);
    setWl(initialWl);
  }, [initialWw, initialWl]);

  // 处理滑块数值变化
  const handleWwChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setWw(Number(event.target.value));
  };

  const handleWlChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setWl(Number(event.target.value));
  };

  // 当鼠标释放时，触发action
  const handleMouseUp = () => {
    // 只有当图片存在时才派发action
    if (uploadedImage) {
      dispatch(adjustWindow(ww, wl));
    }
  };
  
  // 如果没有上传图片，则禁用该组件
  if (!uploadedImage) {
    return (
      <div className="disabled-text">
        <p>上传图像后可调整窗宽窗位</p>
      </div>
    );
  }

  return (
    <div className="window-adjuster">
      {/* 窗宽（WW）滑块 */}
      <div className="slider-container">
        <label htmlFor="ww-slider">窗宽 (WW): {ww}</label>
        <input
          id="ww-slider"
          type="range"
          min="1"
          max="4096" // 通常CT值的范围
          value={ww}
          onChange={handleWwChange}
          onMouseUp={handleMouseUp}
          className="slider"
        />
      </div>
      {/* 窗位（WL）滑块 */}
      <div className="slider-container">
        <label htmlFor="wl-slider">窗位 (WL): {wl}</label>
        <input
          id="wl-slider"
          type="range"
          min="-2000"
          max="2000"
          value={wl}
          onChange={handleWlChange}
          onMouseUp={handleMouseUp}
          className="slider"
        />
      </div>
    </div>
  );
};

export default WindowAdjuster;
