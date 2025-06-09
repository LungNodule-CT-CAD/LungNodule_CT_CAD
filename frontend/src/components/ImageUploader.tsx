import React, { useRef } from 'react';
import { useDispatch } from 'react-redux';
import { uploadImage } from '@store/actions';
import { AppDispatch } from '@store/index';

const ImageUploader: React.FC = () => {
  const dispatch: AppDispatch = useDispatch();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      dispatch(uploadImage(file));
    }
  };

  const handleUploadClick = () => {
    // Trigger the hidden file input
    fileInputRef.current?.click();
  };

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept=".dcm,.dicom" // Accept DICOM files as per README
      />
      <button onClick={handleUploadClick}>上传CT图像</button>
      <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '10px' }}>
        请选择 DICOM 格式的影像文件 (.dcm, .dicom)
      </p>
    </div>
  );
};

export default ImageUploader;
