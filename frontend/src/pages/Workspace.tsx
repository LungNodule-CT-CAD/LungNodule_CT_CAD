import React from 'react';
import { useDispatch } from 'react-redux';
import type { AppDispatch } from '@store/index';
import { detectNodules } from '@store/actions';
import ImageUploader from '@components/ImageUploader';
import ImageViewer from '@components/ImageViewer';
import WindowAdjuster from '@components/WindowAdjuster';
import NoduleList from '@components/NoduleList';
import NoduleZoom from '@components/NoduleZoom';
import ThumbnailList from '@components/ThumbnailList';
import NoduleLocalZoom from '@components/NoduleLocalZoom';
import logo from '@assets/logo.jpeg';

const Workspace: React.FC = () => {
  const dispatch: AppDispatch = useDispatch();

  const handlePredict = async () => {
    await dispatch(detectNodules());
  };

  return (
    <div className="workspace-root" style={{ height: '100%', background: 'var(--main-bg)', padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 顶部Logo与标题 */}
      <div style={{ display: 'flex', alignItems: 'center', height: 72, padding: '8px 16px', borderBottom: '1px solid #1c2a4a', background: 'var(--main-bg)' }}>
        <img src={logo} alt="logo" width={32} height={32} style={{ marginRight: 8 }} />
        <span style={{ fontSize: '1rem', color: 'var(--accent-color)', fontWeight: 700 }}>CT肺结节检测系统</span>
      </div>
      {/* 三栏布局 */}
      <div className="main-layout" style={{ display: 'flex', height: 'calc(100% - 72px)', gap: 0, padding: 0, overflow: 'hidden', minHeight: 0, position: 'relative' }}>
        {/* 左侧面板 */}
        <div className="card panel left-panel" style={{ width: 220, minWidth: 220, maxWidth: 220, display: 'flex', flexDirection: 'column', gap: 8, background: 'var(--panel-bg)', padding: '8px', overflow: 'hidden', zIndex: 2 }}>
          <h3 style={{ marginBottom: 4, fontSize: '0.95rem', textAlign: 'center' }}>图片列表</h3>
          <ImageUploader />
          <hr style={{width: '100%', border: 'none', borderTop: '1px solid #1c2a4a', margin: '8px 0'}} />
          <div style={{flex:1, minHeight:0, overflowY:'auto'}}>
            <ThumbnailList />
          </div>
        </div>
        {/* 主图像区绝对居中 */}
        <div style={{ flex: 1, position: 'relative', minWidth: 0, minHeight: 0, zIndex: 1 }}>
          <div style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: 'min(80vh, 80vw)',
            height: 'min(80vh, 80vw)',
            maxWidth: '100%',
            maxHeight: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--panel-bg)',
            boxShadow: '0 0 8px #0004',
            borderRadius: 12,
            overflow: 'hidden',
          }}>
            <h3 style={{ alignSelf: 'flex-start', fontSize: '1.05rem', marginBottom: 8, padding: '0 8px' }}>图像显示</h3>
            <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, overflow: 'hidden', minHeight: 0 }}>
              <ImageViewer />
            </div>
          </div>
        </div>
        {/* 右侧面板 */}
        <div className="card panel right-panel" style={{ width: 150, minWidth: 150, maxWidth: 150, display: 'flex', flexDirection: 'column', gap: 10, background: 'var(--panel-bg)', padding: '8px', overflow: 'hidden', zIndex: 2 }}>
          <button className="predict-btn" style={{ marginBottom: 8, padding: '8px 0', fontSize: '1rem', background: 'var(--accent-color)', color: '#0a192f', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer' }} onClick={handlePredict}>
            开始预测
          </button>
          <WindowAdjuster />
          <div style={{ marginTop: 8, flex: 1, minHeight: 0, overflowY: 'auto' }}>
            <h4 style={{ fontSize: '0.95rem' }}>检测到的结节列表</h4>
            <NoduleList />
          </div>
        </div>
        {/* 新增右侧放大面板 */}
        <div className="card panel zoom-panel" style={{ width: 250, minWidth: 250, maxWidth: 250, display: 'flex', flexDirection: 'column', alignItems: 'center', background: 'var(--panel-bg)', padding: '12px 8px', overflow: 'hidden', zIndex: 2, marginLeft: 10 }}>
            <NoduleLocalZoom />
        </div>
      </div>
    </div>
  );
};

export default Workspace; 