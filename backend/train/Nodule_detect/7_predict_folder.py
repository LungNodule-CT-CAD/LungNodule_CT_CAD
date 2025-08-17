import torch
import torch.nn as nn
import numpy as np
import cv2
from pathlib import Path
import logging
import pydicom
import argparse
from skimage import measure, transform
from torchvision import transforms
import matplotlib.pyplot as plt
from tqdm import tqdm

# 导入模型定义
from unet_model import UNet
# from cnn_classifier_model import NoduleClassifier
from cnn_classifier_model import get_classifier_model

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 辅助函数 ---
def apply_lung_window(dicom_data):
    pixel_data = dicom_data.pixel_array.astype(np.float32)
    slope = getattr(dicom_data, 'RescaleSlope', 1); intercept = getattr(dicom_data, 'RescaleIntercept', 0)
    hu_image = pixel_data * slope + intercept
    window_center, window_width = -600, 1500
    window_min = window_center - window_width // 2; window_max = window_center + window_width // 2
    windowed_image = np.clip(hu_image, window_min, window_max)
    return (windowed_image - window_min) / (window_max - window_min)

def extract_patches(original_image, prediction_mask, patch_size=64):
    patches = []
    labels = measure.label(prediction_mask, connectivity=2)
    for region in measure.regionprops(labels):
        center_y, center_x = region.centroid
        half_size = patch_size // 2
        start_x = max(0, int(center_x) - half_size); end_x = start_x + patch_size
        start_y = max(0, int(center_y) - half_size); end_y = start_y + patch_size
        if end_x > original_image.shape[1]: end_x = original_image.shape[1]; start_x = end_x - patch_size
        if end_y > original_image.shape[0]: end_y = original_image.shape[0]; start_y = end_y - patch_size
        patch = original_image[start_y:end_y, start_x:end_x]
        if patch.shape != (patch_size, patch_size):
            patch = transform.resize(patch, (patch_size, patch_size), anti_aliasing=True)
        patches.append({'patch': patch, 'region': region})
    return patches
    
# --- 模型加载 ---
def load_unet_model(model_path, device):
    state_dict = torch.load(model_path, map_location=device)
    is_bilinear = 'up1.up.weight' not in state_dict
    model = UNet(n_channels=1, n_classes=1, bilinear=is_bilinear)
    model.load_state_dict(state_dict); model.to(device); model.eval()
    logger.info(f"U-Net模型加载成功: {model_path}")
    return model

def load_cnn_classifier(model_path, device):
    # model = NoduleClassifier()
    model = get_classifier_model()
    model.load_state_dict(torch.load(model_path, map_location=device)); model.to(device); model.eval()
    logger.info(f"CNN分类器加载成功: {model_path}")
    return model

def predict_single_dcm(unet, cnn_classifier, dcm_path, device, class_names, output_dir):
    """对单个DICOM文件执行两阶段预测并保存结果图"""
    try:
        dicom_data = pydicom.dcmread(dcm_path, force=True)
        sop_uid = dicom_data.SOPInstanceUID
    except Exception as e:
        # 在批量处理中，跳过无法读取的文件并记录警告
        logger.warning(f"跳过无法读取的DICOM文件 {dcm_path}: {e}")
        return

    cnn_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])
    img_size = (512, 512)

    image_lung_window = apply_lung_window(dicom_data)
    image_resized = cv2.resize(image_lung_window, img_size, interpolation=cv2.INTER_AREA)
    input_tensor = torch.from_numpy(image_resized).float().unsqueeze(0).unsqueeze(0).to(device)
    
    with torch.no_grad():
        unet_output = unet(input_tensor)
        unet_pred_mask = (unet_output.squeeze().cpu().numpy() > 0.5).astype(np.uint8)

    final_pred_mask = np.zeros_like(unet_pred_mask)
    nodule_count = 0
    if np.sum(unet_pred_mask) > 0:
        candidate_patches = extract_patches(image_resized, unet_pred_mask)
        for cand in candidate_patches:
            # 将单通道灰度 patch 复制为 3 通道，以匹配 EfficientNet 的输入需求
            patch_rgb = np.stack([cand['patch']]*3, axis=-1).astype(np.float32)  # (H, W, 3)
            patch_tensor = cnn_transform(patch_rgb).unsqueeze(0).to(device)
            with torch.no_grad():
                cnn_output = cnn_classifier(patch_tensor)
                _, cnn_pred_idx = torch.max(cnn_output, 1)
            
            if class_names[cnn_pred_idx.item()] == 'tp':
                nodule_count += 1
                min_r, min_c, max_r, max_c = cand['region'].bbox
                final_pred_mask[min_r:max_r, min_c:max_c] |= cand['region'].image
    
    # 只有找到结节时才保存图片，避免生成大量空白图
    if nodule_count > 0:
        plt.figure(figsize=(8, 8))
        plt.imshow(image_resized, cmap='gray')
        red_mask = np.ma.masked_where(final_pred_mask == 0, final_pred_mask)
        plt.imshow(red_mask, cmap='Reds', alpha=0.5)
        plt.title(f'Prediction for {sop_uid}\nFound {nodule_count} Nodule(s)')
        plt.axis('off')
        
        output_path = Path(output_dir) / f"pred_{sop_uid}.png"
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1)
        plt.close()

def main():
    parser = argparse.ArgumentParser(description="对指定文件夹中的所有DICOM文件进行批量两阶段肺结节检测")
    parser.add_argument("--input-dir", "-i", type=str, required=True, help="包含待预测DICOM文件的文件夹路径")
    parser.add_argument("--unet-model", type=str, default="../models/unet/model-best.pth", help="U-Net模型路径")
    parser.add_argument("--cnn-model", type=str, default="../models/cnn_classifier.pth", help="CNN分类器模型路径")
    parser.add_argument("--class-names", type=str, nargs='+', default=['fp', 'tp'], help="CNN分类器的类别名称，顺序必须与训练时一致")
    parser.add_argument("--output-dir", type=str, default="../output/predictions/batch", help="保存预测结果图的目录")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    try:
        unet_model = load_unet_model(args.unet_model, device)
        cnn_model = load_cnn_classifier(args.cnn_model, device)
    except FileNotFoundError as e:
        logger.error(f"模型加载失败: {e}. 请确保模型文件存在.")
        return

    input_path = Path(args.input_dir)
    if not input_path.is_dir():
        logger.error(f"输入路径不是一个有效的目录: {input_path}")
        return

    dcm_files = list(input_path.rglob('*.dcm'))
    if not dcm_files:
        logger.error(f"在目录 {input_path} 中未找到任何 .dcm 文件")
        return

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"在 {input_path} 中找到 {len(dcm_files)} 个DICOM文件，开始批量预测...")

    for dcm_file in tqdm(dcm_files, desc="批量预测DICOM文件"):
        predict_single_dcm(unet_model, cnn_model, dcm_file, device, args.class_names, args.output_dir)

    logger.info("所有预测任务完成！结果保存在: %s", args.output_dir)

if __name__ == '__main__':
    main() 