"""
使用训练好的PyTorch模型进行肺结节检测（两阶段）

此脚本被设计为一个后端模块，通过API接收图像数据并返回检测到的结节坐标。
它加载一个训练好的U-Net（用于候选区域生成）和一个CNN分类器（用于过滤假阳性），
对单张CT图像进行预处理、预测和后处理。
"""

import torch
import numpy as np
import cv2
import pydicom
from io import BytesIO
import os
from scipy import ndimage
from skimage import measure, transform
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from torchvision import transforms


# 从项目中的 unet_model.py 导入 UNet 模型结构
from unet_model import UNet
# 从 cnn_classifier_model.py 导入 CNN 模型结构
from cnn_classifier_model import get_classifier_model


# --- 配置 ---
# 构建模型的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 注意：确保这里的模型路径是正确的
UNET_MODEL_PATH = os.path.join(BASE_DIR, "model-best.pth")
CNN_MODEL_PATH = os.path.join(BASE_DIR, "cnn_classifier.pth")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 模型和预处理所期望的参数
TARGET_IMG_SIZE = (512, 512)
WINDOW_LEVEL = -600  # 肺窗中心
WINDOW_WIDTH = 1500  # 肺窗宽度
CLASS_NAMES = ['fp', 'tp'] # CNN 分类器类别顺序 (与训练一致)

# --- 模型加载 (单例模式) ---
def _load_models_singleton():
    """使用单例模式加载U-Net和CNN模型，避免Web服务中每次请求都重新加载。"""
    unet_model, cnn_model, cnn_transform = None, None, None

    def _load():
        nonlocal unet_model, cnn_model, cnn_transform
        if unet_model is None or cnn_model is None:
            print(f"--- 准备加载模型到设备: {DEVICE} ---")
            try:
                # 1. 加载 U-Net 模型
                unet_state_dict = torch.load(UNET_MODEL_PATH, map_location=DEVICE, weights_only=True)
                is_bilinear = 'up1.up.weight' not in unet_state_dict
                unet_model = UNet(n_channels=1, n_classes=1, bilinear=is_bilinear)
                unet_model.load_state_dict(unet_state_dict)
                unet_model.to(DEVICE)
                unet_model.eval()
                print("--- U-Net 模型加载成功 ---")

                # 2. 加载 CNN 分类器
                cnn_model = get_classifier_model()
                cnn_model.load_state_dict(torch.load(CNN_MODEL_PATH, map_location=DEVICE, weights_only=True))
                cnn_model.to(DEVICE)
                cnn_model.eval()
                print("--- CNN 分类器加载成功 ---")

                # 3. 定义 CNN 输入预处理 (与训练阶段保持一致)
                cnn_transform = transforms.Compose([
                    transforms.ToPILImage(),
                    transforms.Grayscale(num_output_channels=3),
                    transforms.ToTensor(),
                    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
                ])

            except Exception as e:
                print(f"--- 模型加载失败: {e} ---")
                unet_model, cnn_model = None, None
        return unet_model, cnn_model, cnn_transform
    return _load

get_models = _load_models_singleton()


# --- 核心图像处理与预测 ---

def _apply_windowing(image, window_center, window_width):
    """对原始像素值应用窗宽窗位设置"""
    min_value = window_center - window_width / 2
    max_value = window_center + window_width / 2
    image = np.clip(image, min_value, max_value)
    return image

def _preprocess_image(image_bytes: bytes) -> tuple[torch.Tensor | None, np.ndarray | None, tuple[int, int]]:
    """
    预处理图像，优先处理DICOM，并应用肺窗；若失败则按常规图像处理。
    返回处理后的Tensor、用于提取patch的numpy图像和原始图像尺寸。
    """
    original_size = (0, 0)
    image_for_tensor = None

    try:
        # --- 1. 专业DICOM处理流程 ---
        dcm = pydicom.dcmread(BytesIO(image_bytes), force=True)
        pixel_array = dcm.pixel_array
        original_size = (pixel_array.shape[1], pixel_array.shape[0]) # (宽, 高)

        slope = getattr(dcm, 'RescaleSlope', 1)
        intercept = getattr(dcm, 'RescaleIntercept', 0)
        image_hu = pixel_array.astype(np.float32) * slope + intercept
        image_windowed = _apply_windowing(image_hu, WINDOW_LEVEL, WINDOW_WIDTH)

        min_val = WINDOW_LEVEL - WINDOW_WIDTH / 2
        max_val = WINDOW_LEVEL + WINDOW_WIDTH / 2
        image_normalized = (image_windowed - min_val) / (max_val - min_val)
        
        image_for_tensor = image_normalized

    except pydicom.errors.InvalidDicomError:
        # --- 2. 常规图像处理流程 ---
        print("非DICOM格式，尝试作为常规图像文件处理。")
        image_buffer = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(image_buffer, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print("无法解码常规图像。")
            return None, None, (0, 0)
        original_size = (img.shape[1], img.shape[0])
        image_for_tensor = img / 255.0
    
    if image_for_tensor is None:
        return None, None, (0, 0)

    # --- 3. 统一处理：调整大小并转换为Tensor ---
    if image_for_tensor.shape[:2] != TARGET_IMG_SIZE:
        resized_image = cv2.resize(image_for_tensor, TARGET_IMG_SIZE, interpolation=cv2.INTER_LINEAR)
    else:
        resized_image = image_for_tensor
    
    tensor = torch.from_numpy(resized_image).float().unsqueeze(0).unsqueeze(0).to(DEVICE)
    
    return tensor, resized_image, original_size


def _extract_patches_with_watershed(original_image, prob_map, patch_size=64, min_distance=10):
    """使用分水岭算法对 U-Net 概率图进行连通域分割，提取候选 patch"""
    binary_mask = prob_map > 0.5
    distance = ndimage.distance_transform_edt(binary_mask)
    coords = peak_local_max(distance, min_distance=min_distance, labels=binary_mask)
    mask = np.zeros(distance.shape, dtype=bool)
    if coords.size > 0:
        mask[tuple(coords.T)] = True
    markers, _ = ndimage.label(mask)
    labels = watershed(-distance, markers, mask=binary_mask)

    patches = []
    for region in measure.regionprops(labels):
        center_y, center_x = region.centroid
        half_size = patch_size // 2
        start_x = max(0, int(center_x) - half_size)
        end_x = start_x + patch_size
        start_y = max(0, int(center_y) - half_size)
        end_y = start_y + patch_size
        if end_x > original_image.shape[1]:
            end_x = original_image.shape[1]
            start_x = end_x - patch_size
        if end_y > original_image.shape[0]:
            end_y = original_image.shape[0]
            start_y = end_y - patch_size
        
        patch_img = original_image[start_y:end_y, start_x:end_x]
        
        if patch_img.shape != (patch_size, patch_size):
            patch_img = transform.resize(patch_img, (patch_size, patch_size), anti_aliasing=True, preserve_range=True)
            
        patches.append({'patch': patch_img, 'region': region})
    return patches


def run_prediction(image_bytes: bytes) -> list[dict]:
    """
    运行完整的两阶段预测流程（U-Net -> Watershed -> CNN Filter -> Post-processing）。
    """
    unet, cnn_classifier, cnn_transform = get_models()
    if unet is None or cnn_classifier is None:
        print("模型未加载，跳过预测。")
        return []

    # 1. 预处理图像
    input_tensor, resized_image_np, original_size = _preprocess_image(image_bytes)
    if input_tensor is None:
        print("图像预处理失败，无法进行预测。")
        return []
    
    original_w, original_h = original_size

    # 2. Stage-1: U-Net 分割
    with torch.no_grad():
        unet_output = unet(input_tensor)
        unet_pred_prob = unet_output.squeeze().cpu().numpy()
        unet_pred_mask = (unet_pred_prob > 0.5).astype(np.uint8)

    if np.sum(unet_pred_mask) == 0:
        print("U-Net 未检测到候选区域。")
        return []

    # 3. Stage-2: CNN 分类过滤
    candidate_patches = _extract_patches_with_watershed(resized_image_np, unet_pred_prob)
    final_pred_mask = np.zeros_like(unet_pred_mask)

    for cand in candidate_patches:
        patch_for_cnn = (cand['patch'] * 255).astype(np.uint8)
        patch_tensor = cnn_transform(patch_for_cnn).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            cnn_output = cnn_classifier(patch_tensor)
            _, cnn_pred_idx = torch.max(cnn_output, 1)
        
        predicted_class = CLASS_NAMES[cnn_pred_idx.item()]
        if predicted_class == 'tp':
            min_r, min_c, max_r, max_c = cand['region'].bbox
            final_pred_mask[min_r:max_r, min_c:max_c] |= cand['region'].image

    if np.sum(final_pred_mask) == 0:
        print("CNN 分类器过滤后未发现有效结节。")
        return []

    # 4. 后处理 - 将最终掩码转换为轮廓
    resized_mask = cv2.resize(final_pred_mask.astype(np.uint8), (original_w, original_h), interpolation=cv2.INTER_NEAREST)
    contours, _ = cv2.findContours(resized_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    results = []
    for i, cnt in enumerate(contours):
        if cv2.contourArea(cnt) < 10 or len(cnt) < 5:
            continue

        contour_points = [{"x": int(point[0]), "y": int(point[1])} for point in cnt.squeeze(axis=1)]
        
        results.append({
            "id": i + 1,
            "contour": contour_points
        })

    if results:
        print(f"检测到 {len(results)} 个有效结节轮廓。")
    else:
        print("未检测到结节。")
        
    return results 