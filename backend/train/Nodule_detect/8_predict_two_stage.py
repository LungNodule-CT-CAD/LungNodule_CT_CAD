import torch
import numpy as np
import cv2
from pathlib import Path
import logging
import argparse
from tqdm import tqdm
import pydicom
from skimage import measure, transform
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from scipy import ndimage
import matplotlib.pyplot as plt
from torchvision import transforms

# --- 模型定义导入 ---
from unet_model import UNet
from cnn_classifier_model import get_classifier_model

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------- 辅助函数 -------------------- #

def apply_lung_window(dicom_data):
    """将 DICOM Slice 转为肺窗灰度图并归一化到 0-1"""
    pixel_data = dicom_data.pixel_array.astype(np.float32)
    slope = getattr(dicom_data, 'RescaleSlope', 1)
    intercept = getattr(dicom_data, 'RescaleIntercept', 0)
    hu_image = pixel_data * slope + intercept
    window_center, window_width = -600, 1500
    window_min = window_center - window_width // 2
    window_max = window_center + window_width // 2
    windowed_image = np.clip(hu_image, window_min, window_max)
    return (windowed_image - window_min) / (window_max - window_min)


def extract_patches_with_watershed(original_image, prob_map, patch_size=64, min_distance=10):
    """使用分水岭算法对 U-Net 概率图进行连通域分割，提取候选 patch"""
    binary_mask = prob_map > 0.5
    distance = ndimage.distance_transform_edt(binary_mask)
    coords = peak_local_max(distance, min_distance=min_distance, labels=binary_mask)
    mask = np.zeros(distance.shape, dtype=bool)
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
        patch = original_image[start_y:end_y, start_x:end_x]
        # 确保 patch 大小一致
        if patch.shape != (patch_size, patch_size):
            patch = transform.resize(patch, (patch_size, patch_size), anti_aliasing=True)
        patches.append({'patch': patch, 'region': region})
    return patches

# -------------------- 模型加载 -------------------- #

def load_unet_model(model_path, device):
    state_dict = torch.load(model_path, map_location=device)
    is_bilinear = 'up1.up.weight' not in state_dict
    model = UNet(n_channels=1, n_classes=1, bilinear=is_bilinear)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    logger.info(f"U-Net 模型已加载: {model_path}")
    return model


def load_cnn_classifier(model_path, device, arch='efficientnet_b0'):
    """加载 CNN 分类器。如果权重文件不存在则仅返回带 ImageNet 预训练的模型。"""
    model = get_classifier_model(arch=arch)
    if Path(model_path).exists():
        model.load_state_dict(torch.load(model_path, map_location=device))
        logger.info(f"CNN 分类器权重加载成功: {model_path}")
    else:
        logger.warning(f"未找到权重文件 {model_path} ，将使用 ImageNet 预训练权重进行推理 (可能影响效果)")
    model.to(device)
    model.eval()
    return model

# -------------------- 单 Slice 预测 -------------------- #

def predict_single_slice(unet, cnn_classifier, dcm_path, device, cnn_transform, class_names):
    """对单个 DICOM 文件进行两阶段预测，返回最终掩码及结节数量"""
    try:
        dicom_data = pydicom.dcmread(dcm_path, force=True)
        sop_uid = dicom_data.SOPInstanceUID
    except Exception as e:
        logger.warning(f"读取 DICOM 失败，跳过 {dcm_path}: {e}")
        return None, None  # 无结果

    img_size = (512, 512)

    # Stage-1: U-Net 分割
    image_lung_window = apply_lung_window(dicom_data)
    image_resized = cv2.resize(image_lung_window, img_size, interpolation=cv2.INTER_AREA)
    input_tensor = torch.from_numpy(image_resized).float().unsqueeze(0).unsqueeze(0).to(device)

    with torch.no_grad():
        unet_output = unet(input_tensor)
        unet_pred_prob = unet_output.squeeze().cpu().numpy()
        unet_pred_mask = (unet_pred_prob > 0.5).astype(np.uint8)

    # 若没有候选区，直接返回空结果
    if np.sum(unet_pred_mask) == 0:
        return sop_uid, np.zeros_like(unet_pred_mask)

    # Stage-2: CNN 分类过滤
    candidate_patches = extract_patches_with_watershed(image_resized, unet_pred_prob)
    final_pred_mask = np.zeros_like(unet_pred_mask)

    for cand in candidate_patches:
        patch_tensor = cnn_transform(cand['patch'].astype(np.float32)).unsqueeze(0).to(device)
        with torch.no_grad():
            cnn_output = cnn_classifier(patch_tensor)
            _, cnn_pred_idx = torch.max(cnn_output, 1)
        predicted_class = class_names[cnn_pred_idx.item()]
        if predicted_class == 'tp':
            min_r, min_c, max_r, max_c = cand['region'].bbox
            final_pred_mask[min_r:max_r, min_c:max_c] |= cand['region'].image

    return sop_uid, final_pred_mask

# -------------------- 主流程 -------------------- #

def main():
    parser = argparse.ArgumentParser(description="两阶段模型批量预测脚本 (U-Net + CNN)")
    parser.add_argument("--input-dir", "-i", type=str, required=True, help="包含待预测 DICOM 文件的文件夹")
    parser.add_argument("--unet-model", type=str, default="../models/unet/model-finetuned.pth", help="U-Net 模型路径")
    parser.add_argument("--cnn-model", type=str, default="../models/cnn_classifier.pth", help="CNN 分类器权重文件路径")
    parser.add_argument("--cnn-arch", type=str, default="efficientnet_b0", choices=["efficientnet_b0", "resnet101", "resnet100"], help="CNN 分类器所使用的骨干网络架构")
    parser.add_argument("--class-names", type=str, nargs='+', default=['fp', 'tp'], help="CNN 分类器类别顺序 (与训练一致)")
    parser.add_argument("--output-dir", type=str, default="../output/predictions/two_stage", help="保存预测结果的目录")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")

    # 加载模型
    unet = load_unet_model(args.unet_model, device)
    cnn_classifier = load_cnn_classifier(args.cnn_model, device, arch=args.cnn_arch)

    # CNN 输入预处理 (与训练阶段保持一致)
    cnn_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # 创建输出目录
    overlay_dir = Path(args.output_dir) / "overlays"
    mask_dir = Path(args.output_dir) / "masks"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)

    dicom_files = list(Path(args.input_dir).rglob('*.dcm'))
    if not dicom_files:
        logger.error(f"在目录 {args.input_dir} 中未找到任何 .dcm 文件")
        return

    logger.info(f"共找到 {len(dicom_files)} 个 DICOM 文件，开始预测…")

    img_size = (512, 512)
    for dcm_path in tqdm(dicom_files, desc="预测中"):
        sop_uid, pred_mask = predict_single_slice(unet, cnn_classifier, dcm_path, device, cnn_transform, args.class_names)
        if sop_uid is None:
            continue  # 读取失败

        # 仅当存在预测结节时才保存结果，避免空文件
        if np.sum(pred_mask) == 0:
            continue

        # 保存二值掩码 (png，0/255)
        mask_save_path = mask_dir / f"mask_{sop_uid}.png"
        cv2.imwrite(str(mask_save_path), (pred_mask * 255).astype(np.uint8))

        # 保存叠加可视化图
        dicom_data = pydicom.dcmread(dcm_path, force=True)
        image_lung_window = apply_lung_window(dicom_data)
        image_resized = cv2.resize(image_lung_window, img_size, interpolation=cv2.INTER_AREA)

        plt.figure(figsize=(8, 8))
        plt.imshow(image_resized, cmap='gray')
        red_mask = np.ma.masked_where(pred_mask == 0, pred_mask)
        plt.imshow(red_mask, cmap='Reds', alpha=0.5)
        plt.title(f'Slice {sop_uid} | Predicted Nodules')
        plt.axis('off')
        overlay_save_path = overlay_dir / f"overlay_{sop_uid}.png"
        plt.savefig(overlay_save_path, bbox_inches='tight', pad_inches=0.1)
        plt.close()

    logger.info(f"预测完成！掩码保存至: {mask_dir}；叠加图保存至: {overlay_dir}")


if __name__ == '__main__':
    main() 