import os
import torch
import torch.nn as nn
import numpy as np
import cv2
from pathlib import Path
import logging
import json
import pydicom
import argparse
from tqdm import tqdm
from skimage import measure, transform
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from scipy import ndimage
from torchvision import transforms
import pandas as pd
import matplotlib.pyplot as plt

# 导入模型定义
from unet_model import UNet
# from cnn_classifier_model import NoduleClassifier
from cnn_classifier_model import get_classifier_model

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../output/logs/evaluate_two_stage.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 辅助函数 ---
def apply_lung_window(dicom_data):
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
    """
    使用分水岭算法从概率图中分离粘连的结节，并提取patch。
    :param original_image: 原始灰度图 (用于提取patch)。
    :param prob_map: U-Net输出的原始概率图 (0-1之间)。
    :param patch_size: 提取的patch大小。
    :param min_distance: 分水岭算法中两个峰值的最小距离，用于控制分割的灵敏度。
    :return: 提取出的patch列表。
    """
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
        if end_x > original_image.shape[1]: end_x = original_image.shape[1]; start_x = end_x - patch_size
        if end_y > original_image.shape[0]: end_y = original_image.shape[0]; start_y = end_y - patch_size
        patch = original_image[start_y:end_y, start_x:end_x]
        if patch.shape != (patch_size, patch_size):
            patch = transform.resize(patch, (patch_size, patch_size), anti_aliasing=True)
        patches.append({'patch': patch, 'region': region})
    return patches

def get_nodule_masks(ground_truth_json_path):
    masks_dict = {}
    try:
        with open(ground_truth_json_path, 'r') as f:
            inventory = json.load(f)
        for item in inventory:
            mask = cv2.imread(item['mask_path'], cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                masks_dict[item['sop_uid']] = (mask > 0).astype(np.uint8)
    except Exception as e:
        logger.error(f"加载真值掩码失败: {e}")
        return None
    logger.info(f"成功加载 {len(masks_dict)} 个真值掩码")
    return masks_dict

# --- 模型加载 ---
def load_unet_model(model_path, device):
    state_dict = torch.load(model_path, map_location=device)
    is_bilinear = 'up1.up.weight' not in state_dict
    model = UNet(n_channels=1, n_classes=1, bilinear=is_bilinear)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    logger.info(f"U-Net模型加载成功: {model_path}")
    return model

def load_cnn_classifier(model_path, device, arch='efficientnet_b0'):
    """根据架构加载CNN分类器，并加载给定权重文件（若存在）。"""
    model = get_classifier_model(arch=arch)
    if Path(model_path).exists():
        model.load_state_dict(torch.load(model_path, map_location=device))
        logger.info(f"CNN分类器权重加载成功: {model_path} | 架构: {arch}")
    else:
        logger.warning(f"CNN权重文件 {model_path} 不存在，将使用 ImageNet 预训练权重 (arch={arch})")
    model.to(device)
    model.eval()
    return model

def run_two_stage_evaluation(unet, cnn_classifier, dicom_root_dir, nodule_masks, device, class_names, output_dir=None):
    """执行两阶段评估，并可选择性保存可视化结果"""
    
    # CNN输入预处理 - 更新为适配ResNet
    cnn_transform = transforms.Compose([
        transforms.ToPILImage(), # 首先转换为PIL图像
        transforms.Grayscale(num_output_channels=3), # 转换为3通道
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) # ImageNet归一化
    ])

    total_tp_slice, total_fp_slice, total_tn_slice, total_fn_slice = 0, 0, 0, 0
    img_size = (512, 512)
    
    # 读取 DICOM
    dicom_files = list(Path(dicom_root_dir).rglob('*.dcm'))
    logger.info(f"共找到 {len(dicom_files)} 个DICOM文件进行评估")

    # -------- 新增：空目录防护 --------
    if len(dicom_files) == 0:
        logger.warning("目标文件夹内未找到 DICOM 文件，评估终止。")
        return {
            "slice_level_metrics": {},
            "slice_level_confusion_matrix": {}
        }
    # ----------------------------------

    for dcm_file in tqdm(dicom_files, desc="执行两阶段评估"):
        dicom_data = pydicom.dcmread(dcm_file, force=True)
        sop_uid = dicom_data.SOPInstanceUID

        # --- Stage 1: U-Net分割 ---
        image_lung_window = apply_lung_window(dicom_data)
        image_resized = cv2.resize(image_lung_window, img_size, interpolation=cv2.INTER_AREA)
        input_tensor = torch.from_numpy(image_resized).float().unsqueeze(0).unsqueeze(0).to(device)
        
        with torch.no_grad():
            unet_output = unet(input_tensor)
            unet_pred_prob = unet_output.squeeze().cpu().numpy()
            unet_pred_mask = (unet_pred_prob > 0.5).astype(np.uint8)

        # 如果U-Net没有找到任何候选区，则最终预测为空
        if np.sum(unet_pred_mask) == 0:
            final_pred_mask = np.zeros_like(unet_pred_mask)
        else:
            # --- Stage 2: CNN分类过滤 (使用分水岭算法) ---
            candidate_patches = extract_patches_with_watershed(image_resized, unet_pred_prob)
            final_pred_mask = np.zeros_like(unet_pred_mask)

            for cand in candidate_patches:
                # 注意: cand['patch'] 是numpy数组, 需要先转为float32
                patch_tensor = cnn_transform(cand['patch'].astype(np.float32)).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    cnn_output = cnn_classifier(patch_tensor)
                    _, cnn_pred_idx = torch.max(cnn_output, 1)
                
                predicted_class = class_names[cnn_pred_idx.item()]
                
                # 如果CNN认为是'tp' (真结节)，则将该区域加入最终的预测掩码
                if predicted_class == 'tp':
                    min_r, min_c, max_r, max_c = cand['region'].bbox
                    final_pred_mask[min_r:max_r, min_c:max_c] |= cand['region'].image

        # --- 对比评估 ---
        true_mask = nodule_masks.get(sop_uid)
        
        true_mask_resized = np.zeros_like(unet_pred_mask)
        if true_mask is not None:
             if true_mask.shape[:2] != img_size:
                true_mask_resized = cv2.resize(true_mask, img_size, interpolation=cv2.INTER_NEAREST)
             else:
                true_mask_resized = true_mask

        has_nodule_in_gt = np.sum(true_mask_resized) > 0
        has_nodule_in_pred = np.sum(final_pred_mask) > 0

        status = "TN"
        if has_nodule_in_gt and has_nodule_in_pred: status = "TP"
        elif not has_nodule_in_gt and has_nodule_in_pred: status = "FP"
        elif has_nodule_in_gt and not has_nodule_in_pred: status = "FN"

        # --- 保存可视化结果 (仅保存TP, FP, FN) ---
        if output_dir and status != "TN":
            fig, axes = plt.subplots(1, 4, figsize=(24, 6))
            fig.suptitle(f'Slice: {sop_uid} | Final Status: {status}', fontsize=16)

            # 原始图像
            axes[0].imshow(image_resized, cmap='gray')
            axes[0].set_title('Original Image (Lung Window)')
            axes[0].axis('off')

            # 真实掩码
            axes[1].imshow(true_mask_resized, cmap='hot', vmin=0, vmax=1)
            axes[1].set_title('Ground Truth Mask')
            axes[1].axis('off')

            # U-Net 原始预测
            axes[2].imshow(unet_pred_mask, cmap='hot', vmin=0, vmax=1)
            axes[2].set_title('U-Net Raw Prediction')
            axes[2].axis('off')
            
            # CNN过滤后最终预测
            axes[3].imshow(final_pred_mask, cmap='hot', vmin=0, vmax=1)
            axes[3].set_title('Final Prediction')
            axes[3].axis('off')
            
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            save_path = Path(output_dir) / f"{status}_{sop_uid}.png"
            plt.savefig(save_path)
            plt.close(fig)

        if has_nodule_in_gt and has_nodule_in_pred: total_tp_slice += 1
        elif not has_nodule_in_gt and has_nodule_in_pred: total_fp_slice += 1
        elif has_nodule_in_gt and not has_nodule_in_pred: total_fn_slice += 1

    # --- 汇总与计算 ---
    recall = total_tp_slice / (total_tp_slice + total_fn_slice) if (total_tp_slice + total_fn_slice) > 0 else 0.0
    precision = total_tp_slice / (total_tp_slice + total_fp_slice) if (total_tp_slice + total_fp_slice) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    total_tn_slice = len(dicom_files) - (total_tp_slice + total_fp_slice + total_fn_slice)
    denom = len(dicom_files)
    accuracy = (total_tp_slice + total_tn_slice) / denom if denom else 0.0
    
    results = {
        "slice_level_metrics": {
            "accuracy": accuracy, "recall_sensitivity": recall,
            "precision": precision, "f1_score": f1,
            "total_false_positives": total_fp_slice
        },
        "slice_level_confusion_matrix": {
            "TP": total_tp_slice, "FP": total_fp_slice,
            "TN": total_tn_slice, "FN": total_fn_slice
        }
    }
    return results

def main():
    parser = argparse.ArgumentParser(description="执行U-Net + CNN的两阶段肺结节检测评估")
    parser.add_argument("--unet-model", type=str, default="../models/unet/model-finetuned.pth", help="U-Net模型路径")
    parser.add_argument("--cnn-model", type=str, default="../models/cnn_resnet101.pth", help="CNN分类器权重文件路径")
    parser.add_argument("--cnn-arch", type=str, default="resnet101", choices=["efficientnet_b0", "resnet101"], help="CNN分类器骨干网络架构")
    parser.add_argument("--dicom-dir", type=str, default="/root/Lung/ver2/Nodule-Detec/U-net/data/test/LIDC-IDRI-0002", help="DICOM数据根目录")
    parser.add_argument("--ground-truth-json", type=str, default="../data/processed/ground_truth_dataset/ground_truth_inventory.json", help="真值清单JSON文件")
    parser.add_argument("--class-names", type=str, nargs='+', default=['fp', 'tp'], help="CNN分类器的类别名称，顺序必须与训练时一致")
    parser.add_argument("--output-dir", type=str, default="../output/predictions/evaluation_fn", help="保存最终可视化结果的目录")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")
    
    # 加载模型
    unet_model = load_unet_model(args.unet_model, device)
    cnn_model = load_cnn_classifier(args.cnn_model, device, arch=args.cnn_arch)
    
    # 加载真值
    nodule_masks = get_nodule_masks(args.ground_truth_json)
    if nodule_masks is None: return

    # 创建输出目录
    if args.output_dir:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"可视化结果将保存至: {args.output_dir}")

    # 执行评估
    results = run_two_stage_evaluation(unet_model, cnn_model, args.dicom_dir, nodule_masks, device, args.class_names, args.output_dir)

    # 打印报告
    logger.info("\n\n===== 两阶段模型最终评估报告 =====")
    metrics = results['slice_level_metrics']
    cm = results['slice_level_confusion_matrix']
    logger.info("--- 切片级评估指标 (Slice-Level Metrics) ---")
    logger.info(f"召回率 (Recall/Sensitivity): {metrics['recall_sensitivity']:.4f} (在{cm['TP']+cm['FN']}个真阳性切片中，正确找到了{cm['TP']}个)")
    logger.info(f"精确率 (Precision): {metrics['precision']:.4f}")
    logger.info(f"F1分数 (F1-Score): {metrics['f1_score']:.4f}")
    logger.info(f"准确率 (Accuracy): {metrics['accuracy']:.4f}")
    logger.info(f"假阳性切片总数 (Total False Positives): {cm['FP']}")
    logger.info(f"切片级混淆矩阵: TP={cm['TP']}, FP={cm['FP']}, TN={cm['TN']}, FN={cm['FN']}")

if __name__ == '__main__':
    main() 
#     python 5_evaluate_two_stage.py \
#   --cnn-model ../models/cnn_resnet101.pth \
#   --cnn-arch resnet101 \
#   --unet-model ../models/unet/model-finetuned.pth \
#   --dicom-dir /root/Lung/ver2/Nodule-Detec/U-net/data/raw/LIDC-IDRI-0010 \
#   --ground-truth-json ../data/processed/ground_truth_dataset/ground_truth_inventory.json

