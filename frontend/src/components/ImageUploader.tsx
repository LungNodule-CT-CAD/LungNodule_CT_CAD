// src/components/ImageUploader.tsx

// 导入React核心模块及钩子：useRef用于获取DOM元素引用
import React, { useRef } from 'react';
// 导入Redux与React的连接钩子：useDispatch用于获取Redux的dispatch函数
import { useDispatch } from 'react-redux';
// 导入自定义上传图像的异步action：触发文件上传逻辑并更新Redux状态
import { uploadImages } from '@store/actions';
// 导入Redux的dispatch类型：用于类型注解，确保dispatch函数的类型正确性
import { AppDispatch } from '@store/index';


/**
 * DICOM图像上传组件（核心功能组件）
 * 提供用户交互入口，支持选择DICOM格式文件并触发上传流程
 * 与Redux集成，通过dispatch分发action更新全局状态
 */
const ImageUploader: React.FC = () => {
  // 获取Redux的dispatch函数（用于分发action到store）
  const dispatch: AppDispatch = useDispatch();

  // 使用useRef创建ref对象（用于获取文件输入框的DOM引用）
  // 初始值为null，类型为HTMLInputElement（文件输入框的DOM类型）
  const fileInputRef = useRef<HTMLInputElement>(null);


  /**
   * 文件选择事件处理函数（核心逻辑）
   * 当用户通过文件选择框选中文件后触发
   * @param event - React的ChangeEvent事件对象（包含文件输入框的状态）
   */
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      // 将FileList转换为File[]
      dispatch(uploadImages(Array.from(files)));
    }
    // 清空input的值，确保下次选择相同文件时仍然触发onChange
    if(fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };


  /**
   * 上传按钮点击处理函数（交互优化逻辑）
   * 用于间接触发隐藏的文件输入框的点击事件（替代原生文件选择框样式）
   */
  const handleUploadClick = () => {
    // 通过ref获取文件输入框的DOM实例，并调用其click()方法（打开文件选择对话框）
    // 使用可选链?.避免ref未挂载时（如组件未渲染完成）调用click()导致的错误
    fileInputRef.current?.click();
  };


  // 组件渲染的UI结构（用户实际看到的交互界面）
  return (
    <div>
      {/* 隐藏的文件输入框（核心交互元素，但通过样式隐藏原生外观） */}
      <input
        type="file"                // 类型为文件选择框（HTML标准输入类型）
        ref={fileInputRef}         // 关联ref对象（用于后续通过JS控制输入框行为）
        onChange={handleFileChange}// 文件选择变化时触发的回调函数（处理文件上传）
        style={{ display: 'none' }}// 隐藏输入框（通过自定义按钮替代原生样式，提升UI一致性）
        accept=".dcm,.dicom,.jpg,.png" // 接受更多图片格式
        multiple // 允许选择多个文件
      />

      {/* 自定义上传按钮（用户实际点击的交互入口） */}
      <button onClick={handleUploadClick} style={{ width: '100%', padding: '6px 0', fontSize: '0.9rem' }}>
        上传图像
      </button>

      {/* 文件格式提示文字（辅助用户操作） */}
      {/* <p className="uploader-info">
        请选择 DICOM 格式的影像文件 (.dcm, .dicom)
      </p> */}
    </div>
  );
};

// 导出组件（供其他模块引入使用，如App组件中集成）
export default ImageUploader;