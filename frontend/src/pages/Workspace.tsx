import React, { useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import type { AppDispatch, RootState } from '@store/index';
import { detectNodules } from '@store/actions';
import ImageUploader from '@components/ImageUploader';
import ImageViewer from '@components/ImageViewer';
import WindowAdjuster from '@components/WindowAdjuster';
import NoduleList from '@components/NoduleList';
import ThumbnailList from '@components/ThumbnailList';
import NoduleLocalZoom from '@components/NoduleLocalZoom';
import logo from '@assets/logo.jpeg';

const Workspace: React.FC = () => {
  const dispatch: AppDispatch = useDispatch();
  const detectStatus = useSelector((state: RootState) => state.detectStatus);
  const { images, activeImageId } = useSelector((state: RootState) => state);
  const activeImage = images.find(img => img.id === activeImageId);
  const patientId = activeImage?.isDicom ? activeImage?.patientId : undefined;
  const imageViewerRef = useRef<{ reset: () => void }>(null);

  const handlePredict = async () => {
    await dispatch(detectNodules());
  };

  return (
    <div className="workspace-root" style={{ height: '100%', background: 'var(--main-bg)', padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 顶部Logo与标题 */}
      <div style={{ display: 'flex', alignItems: 'center', height: 72, padding: '8px 16px', borderBottom: '1px solid #1c2a4a', background: 'var(--main-bg)', position: 'relative' }}>
        <img src={logo} alt="logo" width={32} height={32} style={{ marginRight: 8 }} />
        <span style={{ fontSize: '1rem', color: 'var(--accent-color)', fontWeight: 700 }}>CT肺结节检测系统</span>
        {patientId && (
          <span style={{ position: 'absolute', right: 24, top: 16, color: '#64ffda', fontWeight: 600, fontSize: '1rem', letterSpacing: 1 }}>
            Patient ID: {patientId}
          </span>
        )}
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
            <div style={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between', marginBottom: 8, padding: '0 8px' }}>
              <h3 style={{ fontSize: '1.05rem', margin: 0 }}>图像显示</h3>
              <button
                onClick={() => imageViewerRef.current?.reset()}
                style={{ background: 'none', color: '#64ffda', border: 'none', fontWeight: 600, fontSize: '0.98rem', cursor: 'pointer', padding: '2px 12px', borderRadius: 6, transition: 'background 0.2s', marginLeft: 8 }}
                onMouseOver={e => (e.currentTarget.style.background = '#18324a')}
                onMouseOut={e => (e.currentTarget.style.background = 'none')}
              >
                复位
              </button>
            </div>
            <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, overflow: 'hidden', minHeight: 0 }}>
              <ImageViewer ref={imageViewerRef} />
            </div>
          </div>
        </div>
        {/* 右侧面板 */}
        <div className="card panel right-panel" style={{ width: 150, minWidth: 150, maxWidth: 150, display: 'flex', flexDirection: 'column', gap: 10, background: 'var(--panel-bg)', padding: '8px', overflow: 'hidden', zIndex: 2 }}>
          <button onClick={handlePredict}>
            开始预测
          </button>
          <WindowAdjuster />
          <div style={{ marginTop: 8, flex: 1, minHeight: 0, overflowY: 'auto' }}>
            {detectStatus === 'detecting' && (
              <div style={{color:'#64ffda', textAlign:'center', marginTop:24, fontWeight:600, fontSize:'1rem'}}>检测中...</div>
            )}
            {detectStatus === 'detected' && (
              <>
                <h4 style={{ fontSize: '0.95rem' }}>检测到的结节列表</h4>
                <NoduleList />
              </>
            )}
            {detectStatus === 'not_found' && (
              <div style={{color:'#ccc', textAlign:'center', marginTop:24, fontWeight:500, fontSize:'1rem'}}>当前图像未检测到结节。</div>
            )}
            {/* not_started时不显示任何结节相关内容 */}
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