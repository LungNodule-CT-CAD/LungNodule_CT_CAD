import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@store/index';
import { selectNodule } from '@store/actions';
import { Nodule } from '@store/types';

/**
 * 结节列表组件
 * - 从Redux store中获取检测到的结节列表并展示。
 * - 允许用户点击选择某个结节。
 * - 高亮显示当前被选中的结节。
 */
const NoduleList: React.FC = () => {
  // 从Redux store中获取结节列表和当前选中的结节
  const { nodules, selectedNodule } = useSelector((state: RootState) => state);
  const dispatch: AppDispatch = useDispatch();

  // 处理结节选择事件
  const handleSelectNodule = (nodule: Nodule) => {
    // dispatch 'selectNodule' action来更新store
    dispatch(selectNodule(nodule));
  };

  // 如果没有结节数据，则显示提示信息
  if (nodules.length === 0) {
    return <p>尚未检测到结节。请先上传图像并运行检测。</p>;
  }

  return (
    <div className="nodule-list-container">
      <h4>检测到的结节列表</h4>
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
              结节 #{nodule.id} - 坐标: ({nodule.x}, {nodule.y})
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default NoduleList;
