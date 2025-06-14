import React, { useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '@store/index';
import { setActiveImage } from '@store/actions';
import { ImageFile } from '@store/types';
import cornerstone from 'cornerstone-core';

// 单个缩略图项的组件
const ThumbnailItem: React.FC<{ image: ImageFile }> = ({ image }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
  
    useEffect(() => {
      const canvas = canvasRef.current;
      let isComponentMounted = true; // 标志位，用于防止在卸载后执行异步代码

      if (image.isDicom && canvas) {
        // 确保canvas有尺寸，否则viewport计算会出错
        canvas.width = 128;
        canvas.height = 128;

        cornerstone.enable(canvas); // <--- 直接在Canvas上启用
  
        cornerstone.loadImage(image.imageUrl).then(loadedImage => {
          if (isComponentMounted && canvas) {
            const viewport = cornerstone.getDefaultViewportForImage(canvas, loadedImage);
            cornerstone.renderToCanvas(canvas, loadedImage, viewport);
            cornerstone.disable(canvas); // <--- 渲染后禁用，释放资源
          }
        }).catch(err => {
            console.error(`Failed to load thumbnail for ${image.id}:`, err);
            if (isComponentMounted && canvas) {
                const ctx = canvas.getContext('2d');
                if(ctx) {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.fillStyle = 'red';
                    ctx.font = '10px sans-serif';
                    ctx.fillText('加载失败', 10, 20);
                }
            }
        });
      }
      
      return () => {
          isComponentMounted = false;
          try {
            if (canvas && cornerstone.getEnabledElement(canvas).element) {
                cornerstone.disable(canvas);
            }
          } catch (e) {
            // 忽略错误，因为元素可能已经被禁用或移除
          }

          if (!image.isDicom) {
              URL.revokeObjectURL(image.imageUrl);
          }
      };
    }, [image]);
  
    if (image.isDicom) {
      return <canvas ref={canvasRef} style={{ width: '100%', display: 'block' }} />;
    } else {
      return <img src={image.imageUrl} alt={image.file.name} style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '2px' }} />;
    }
  };

const ThumbnailList: React.FC = () => {
  const { images, activeImageId } = useSelector((state: RootState) => state);
  const dispatch: AppDispatch = useDispatch();

  const handleThumbnailClick = (imageId: string) => {
    dispatch(setActiveImage(imageId));
  };

  if (images.length === 0) {
    return (
        <div style={{ flex: 1, overflowY: 'auto', border: '1px dashed #1c2a4a', borderRadius: 8, minHeight: 60, display: 'flex', flexDirection: 'column', gap: 4, justifyContent: 'center', alignItems: 'center', color: '#888', padding: '8px' }}>
            <span>请先上传图像</span>
        </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', minHeight: 60, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {images.map((image: ImageFile) => (
        <div
          key={image.id}
          onClick={() => handleThumbnailClick(image.id)}
          style={{
            cursor: 'pointer',
            border: `2px solid ${image.id === activeImageId ? 'var(--accent-color)' : 'transparent'}`,
            borderRadius: '4px',
            padding: '2px',
            background: '#2a3b5c'
          }}
        >
          <ThumbnailItem image={image} />
          <p style={{
             fontSize: '0.7rem', 
             margin: '4px 0 0', 
             color: '#eee', 
             textAlign: 'center',
             wordBreak: 'break-all'
            }}>
                {image.file.name}
            </p>
        </div>
      ))}
    </div>
  );
};

export default ThumbnailList; 