"""
使用训练好的PyTorch U-Net模型预测肺结节

此脚本被设计为一个后端模块，通过API接收图像数据并返回检测到的结节坐标。
它加载一个训练好的U-Net模型，对单张CT图像进行预处理、预测和后处理。
"""

import torch
import numpy as np
import cv2
import pydicom
from io import BytesIO
import os
from scipy import ndimage
import torch.nn.functional as F

# 从项目中的 model.py 导入 UNet 模型结构
from model import UNet

# --- 配置 ---
# 构建模型的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 注意：确保这里的模型路径是正确的，指向你的最佳模型
MODEL_PATH = os.path.join(BASE_DIR, "model-best.pth") 
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 模型和预处理所期望的参数
TARGET_IMG_SIZE = (512, 512)
WINDOW_LEVEL = -600  # 肺窗中心
WINDOW_WIDTH = 1500  # 肺窗宽度

# --- 模型加载 (单例模式) ---
def _load_model_singleton():
    """使用单例模式加载模型，避免Web服务中每次请求都重新加载。"""
    model = None
    def _load():
        nonlocal model
        if model is None:
            print(f"--- 准备加载模型到设备: {DEVICE} ---")
            try:
                # 1. 创建 UNet 模型的实例
                # model-best.pth 是使用 bilinear=True 训练的
                model = UNet(n_channels=1, n_classes=1, bilinear=True)
                
                # 2. 将模型移动到指定设备
                model.to(DEVICE)
                
                # 3. 加载模型的权重
                # strict=False 允许在模型结构和权重文件有轻微不匹配时也能加载
                state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
                model.load_state_dict(state_dict, strict=False)

                # 4. 设置为评估模式
                model.eval()
                print("--- 模型加载成功 ---")
            except Exception as e:
                print(f"--- 模型加载失败: {e} ---")
                model = None # 确保失败时 model 状态为 None
        return model
    return _load

get_model = _load_model_singleton()


# --- 核心图像处理与预测 ---

def _apply_windowing(image, window_center, window_width):
    """对原始像素值应用窗宽窗位设置"""
    min_value = window_center - window_width / 2
    max_value = window_center + window_width / 2
    image = np.clip(image, min_value, max_value)
    return image

def _preprocess_image(image_bytes: bytes) -> tuple[torch.Tensor | None, tuple[int, int]]:
    """
    预处理图像，优先处理DICOM，并应用肺窗；若失败则按常规图像处理。
    返回处理后的Tensor和原始图像尺寸。
    """
    original_size = (0, 0)
    image_for_tensor = None

    try:
        # --- 1. 专业DICOM处理流程 ---
        dcm = pydicom.dcmread(BytesIO(image_bytes), force=True)
        pixel_array = dcm.pixel_array
        original_size = (pixel_array.shape[1], pixel_array.shape[0]) # (宽, 高)

        # 应用HU值转换
        slope = getattr(dcm, 'RescaleSlope', 1)
        intercept = getattr(dcm, 'RescaleIntercept', 0)
        image_hu = pixel_array.astype(np.float32) * slope + intercept

        # 应用肺窗
        image_windowed = _apply_windowing(image_hu, WINDOW_LEVEL, WINDOW_WIDTH)
        
        # 归一化到 [0, 255]
        min_val = WINDOW_LEVEL - WINDOW_WIDTH / 2
        max_val = WINDOW_LEVEL + WINDOW_WIDTH / 2
        image_normalized = ((image_windowed - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
        
        image_for_tensor = image_normalized

    except pydicom.errors.InvalidDicomError:
        # --- 2. 常规图像处理流程 ---
        print("非DICOM格式，尝试作为常规图像文件处理。")
        image_buffer = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(image_buffer, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print("无法解码常规图像。")
            return None, (0, 0)
        original_size = (img.shape[1], img.shape[0])
        image_for_tensor = img
    
    if image_for_tensor is None:
        return None, (0, 0)

    # --- 3. 统一处理：调整大小、归一化并转换为Tensor ---
    # 调整大小
    if image_for_tensor.shape[:2] != TARGET_IMG_SIZE:
        resized_image = cv2.resize(image_for_tensor, TARGET_IMG_SIZE, interpolation=cv2.INTER_LINEAR)
    else:
        resized_image = image_for_tensor

    # 归一化到 [0, 1]
    normalized_for_tensor = resized_image / 255.0
    
    # 转换为Pytorch张量并调整维度 (B, C, H, W)
    tensor = torch.from_numpy(normalized_for_tensor).float().unsqueeze(0).unsqueeze(0).to(DEVICE)
    
    return tensor, original_size

def _find_connected_components(binary_mask, min_size=20):
    """
    查找二值掩码中的连通区域，并过滤掉小于min_size的区域。
    这有助于消除小的噪声点。
    """
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    
    filtered_mask = np.zeros_like(binary_mask)
    for i in range(1, num_labels):  # 跳过背景（标签0）
        if stats[i, cv2.CC_STAT_AREA] >= min_size:
            filtered_mask[labels == i] = 255 # 使用255以便后续轮廓查找
    
    return filtered_mask.astype(np.uint8)


def run_prediction(image_bytes: bytes) -> list[dict]:
    """
    运行完整的预测流程（预处理 -> 推理 -> 后处理）。
    这是提供给外部API调用的主函数。
    """
    model = get_model()
    if model is None:
        print("模型未加载，跳过预测。")
        return []

    # 1. 预处理图像
    input_tensor, original_size = _preprocess_image(image_bytes)
    if input_tensor is None:
        print("图像预处理失败，无法进行预测。")
        return []
    
    original_w, original_h = original_size

    # 2. 模型推理
    with torch.no_grad():
        # 模型输出是logits，需要通过sigmoid转换为概率
        prediction = model(input_tensor)
    
    # 将概率掩码移到CPU，并移除batch和channel维度
    pred_mask = prediction.squeeze().cpu().numpy()
    
    # 3. 后处理 - 从分割蒙版提取边界框
    # 根据置信度阈值生成二进制蒙版
    confidence_threshold = 0.5
    binary_mask = (pred_mask > confidence_threshold).astype(np.uint8)

    # 过滤掉过小的噪声区域
    filtered_mask_small = _find_connected_components(binary_mask)

    # 将最终的掩码缩放回原始图像尺寸，使用最近邻插值以保持边缘清晰
    resized_mask = cv2.resize(filtered_mask_small, (original_w, original_h), interpolation=cv2.INTER_NEAREST)

    # 寻找检测到的结节的轮廓
    contours, _ = cv2.findContours(resized_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    results = []
    for i, cnt in enumerate(contours):
        # 过滤掉点数过少或面积过小的轮廓，避免噪声
        # contourArea计算轮廓面积，len(cnt)获取轮廓点数
        if cv2.contourArea(cnt) < 10 or len(cnt) < 5:
            continue

        # 将轮廓点从OpenCV的 [[[x, y]]] 格式转换为 [{"x": x, "y": y}] 列表
        # .squeeze(axis=1) 将 (N, 1, 2) 数组压缩为 (N, 2)
        contour_points = [{"x": int(point[0]), "y": int(point[1])} for point in cnt.squeeze(axis=1)]
        
        results.append({
            "id": i + 1,
            "contour": contour_points
        })

    if contours:
        print(f"检测到 {len(results)} 个有效结节轮廓。")
    else:
        print("未检测到结节。")
        
    return results 