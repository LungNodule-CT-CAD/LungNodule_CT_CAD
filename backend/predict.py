import torch
import numpy as np
import cv2
import pydicom
from PIL import Image
from io import BytesIO
import os

# 从我们新创建的 model.py 中导入 UNet 模型结构
from model import UNet

# --- 配置 ---
# 构建模型的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best_model.pth")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 模型和预处理所期望的参数
TARGET_IMG_SIZE = (512, 512)
WINDOW_LEVEL = -600
WINDOW_WIDTH = 1500

# --- 模型加载 ---
def _load_model_singleton():
    model = None
    def _load():
        nonlocal model
        if model is None:
            print(f"--- 准备加载模型到设备: {DEVICE} ---")
            try:
                # 1. 创建 UNet 模型的实例
                model = UNet(n_channels=1, n_classes=1, bilinear=False)
                
                # 2. 将模型移动到指定设备
                model.to(DEVICE)
                
                # 3. 加载模型的权重 (state_dict)
                # 添加 weights_only=True 以提高安全性，并消除警告
                state_dict = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
                model.load_state_dict(state_dict)

                # 4. 设置为评估模式
                model.eval()
                print("--- 模型加载成功 ---")
            except Exception as e:
                print(f"--- 模型加载失败: {e} ---")
                model = None # 确保失败时 model 状态为 None
        return model
    return _load

get_model = _load_model_singleton()

# --- 图像预处理 ---
def _preprocess_image(image_bytes: bytes) -> tuple[torch.Tensor, tuple[int, int]]:
    """
    预处理图像，优先处理 DICOM 格式，并应用肺窗；若失败则按常规图像处理。
    """
    original_size = (0, 0)
    img_resized_for_tensor = None

    try:
        # --- 专业 DICOM 处理流程 ---
        dcm = pydicom.dcmread(BytesIO(image_bytes), force=True)
        pixel_array = dcm.pixel_array.astype(np.float32)
        original_size = (pixel_array.shape[1], pixel_array.shape[0]) # (宽, 高)

        # 应用 Hounsfield Unit (HU) 转换
        slope = getattr(dcm, 'RescaleSlope', 1)
        intercept = getattr(dcm, 'RescaleIntercept', 0)
        image_hu = pixel_array * slope + intercept

        # 应用肺窗
        lower_bound = WINDOW_LEVEL - (WINDOW_WIDTH / 2)
        upper_bound = WINDOW_LEVEL + (WINDOW_WIDTH / 2)
        image_windowed = np.clip(image_hu, lower_bound, upper_bound)
        
        # 归一化以输入网络
        image_normalized = (image_windowed - lower_bound) / (upper_bound - lower_bound)
        
        # 调整大小
        img_resized_for_tensor = cv2.resize(image_normalized, TARGET_IMG_SIZE, interpolation=cv2.INTER_LINEAR)

    except pydicom.errors.InvalidDicomError:
        # --- 常规图像处理流程 ---
        image_stream = BytesIO(image_bytes)
        img = Image.open(image_stream).convert("L") # 转换为灰度图
        original_size = img.size # (宽, 高)
        img_array = np.array(img, dtype=np.float32) / 255.0 # 归一化到 [0, 1]
        
        # 调整大小
        img_resized_for_tensor = cv2.resize(img_array, TARGET_IMG_SIZE, interpolation=cv2.INTER_LINEAR)

    # 转换为 Tensor，并添加 batch 和 channel 维度
    tensor = torch.from_numpy(img_resized_for_tensor).unsqueeze(0).unsqueeze(0).to(device=DEVICE, dtype=torch.float32)
    return tensor, original_size


# --- 核心预测与后处理 ---
def run_prediction(image_bytes: bytes) -> list[dict]:
    """
    运行完整的预测流程（预处理 -> 推理 -> 后处理）。
    """
    model = get_model()
    if model is None:
        print("模型未加载，跳过预测。")
        return []

    # 1. 预处理图像
    input_tensor, original_size = _preprocess_image(image_bytes)
    original_w, original_h = original_size
    if original_w == 0 or original_h == 0:
        return [] # 如果无法解析图像尺寸，则返回空

    # 2. 模型推理
    with torch.no_grad():
        pred_logits = model(input_tensor)
        # 应用 Sigmoid 函数将输出转换为概率
        pred_probs = torch.sigmoid(pred_logits)

    # 3. 后处理 - 从分割蒙版提取边界框
    # 将概率蒙版移动到 CPU，移除 batch 和 channel 维度
    pred_mask = pred_probs.squeeze().cpu().numpy()
    
    # 根据置信度阈值生成二进制蒙版
    confidence_threshold = 0.5
    binary_mask = (pred_mask > confidence_threshold).astype(np.uint8)

    # 将蒙版缩放回原始图像尺寸，使用最近邻插值以保持边缘清晰
    resized_mask = cv2.resize(binary_mask, (original_w, original_h), interpolation=cv2.INTER_NEAREST)

    # 寻找检测到的结节的轮廓
    contours, _ = cv2.findContours(resized_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    results = []
    for i, cnt in enumerate(contours):
        # 对于每个轮廓，计算其最小外接矩形
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 过滤掉过小的检测结果，避免噪声
        if w > 5 and h > 5:
            results.append({
                "id": i + 1,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            })

    return results 