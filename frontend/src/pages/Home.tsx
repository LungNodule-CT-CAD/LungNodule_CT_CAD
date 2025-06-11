import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@store/index';
import { detectNodules } from '@store/actions';

import ImageUploader from '@components/ImageUploader';
import ImageViewer from '@components/ImageViewer';
import WindowAdjuster from '@components/WindowAdjuster';
import NoduleList from '@components/NoduleList';
import NoduleZoom from '@components/NoduleZoom';
import logo from '@assets/logo.jpeg';

const Home: React.FC = () => {
  const dispatch: AppDispatch = useDispatch();
  const { uploadedImage } = useSelector((state: RootState) => state);

  // "检测结节"按钮的点击处理函数
  const handleDetectClick = () => {
    dispatch(detectNodules());
  };

  return (
    <>
      <div className="home-container">
        <img src={logo} alt="logo" width={100} height={100} />
        <h1>CT 肺结节检测系统</h1>
      </div>

      <div className="main-layout">
        {/* 左侧控制面板 */}
        <div className="card panel control-panel">
          <h3>控制面板</h3>
          <ImageUploader />
          <WindowAdjuster />
          {/* 只有上传了图片才能进行检测 */}
          {uploadedImage && (
            <button onClick={handleDetectClick}>
              检测结节
            </button>
          )}
        </div>

        {/* 中间图像显示区域 */}
        <div className="card panel image-panel">
          <h3>图像显示</h3>
          <ImageViewer />
        </div>

        {/* 右侧结节列表区域 */}
        <div className="card panel">
          <h3>结节详情</h3>
          <NoduleList />
          <NoduleZoom />
        </div>
      </div>

      <p className="read-the-docs">
        请上传您的 CT 影像以开始分析
      </p>
    </>
  );
}

export default Home;
