import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@store/index';
import { selectNodule } from '@store/actions';
import { Nodule } from '@store/types';

/**
 * 结节列表组件
 * - 从Redux store中获取活动图像的结节列表并展示。
 * - 允许用户点击选择某个结节。
 * - 高亮显示当前被选中的结节。
 */
const NoduleList: React.FC = () => {
  // 从Redux store中获取结节列表和当前选中的结节
  const { images, activeImageId, selectedNodule } = useSelector((state: RootState) => state);
  const dispatch: AppDispatch = useDispatch();

  const activeImage = images.find(img => img.id === activeImageId);
  const nodules = activeImage ? activeImage.nodules : [];

  // 处理结节选择事件
  const handleSelectNodule = (nodule: Nodule) => {
    dispatch(selectNodule(nodule));
  };

  if (!activeImage) {
    return <p>请先选择一张图像。</p>;
  }

  // 如果没有结节数据，则显示提示信息
  if (nodules.length === 0) {
    return <p>当前图像尚未检测到结节。</p>;
  }

  return (
    <div className="nodule-list-container">
      <div className="nodule-list">
        {nodules.map(nodule => {
          // 动态组合类名：基础类名 + 是否选中的条件类名
          const buttonClasses = `nodule-button ${selectedNodule?.id === nodule.id ? 'selected' : ''}`;
          
          return (
            <button
              key={nodule.id}
              onClick={() => handleSelectNodule(nodule)}
              className={buttonClasses.trim()} // trim() 确保没有多余的空格
            >
              结节 #{nodule.id}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default NoduleList;
