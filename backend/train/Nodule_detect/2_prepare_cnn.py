import os
import torch
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

from unet_model import UNet

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("prepare_cnn_dataset.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def apply_lung_window(dicom_data):
    """对DICOM应用肺窗并归一化到0-1."""
    pixel_data = dicom_data.pixel_array.astype(np.float32)
    slope = getattr(dicom_data, 'RescaleSlope', 1)
    intercept = getattr(dicom_data, 'RescaleIntercept', 0)
    hu_image = pixel_data * slope + intercept
    
    window_center = -600
    window_width = 1500
    window_min = window_center - window_width // 2
    window_max = window_center + window_width // 2
    
    windowed_image = np.clip(hu_image, window_min, window_max)
    
    normalized = (windowed_image - window_min) / (window_max - window_min)
    return normalized

def extract_patches_with_watershed(original_image, prob_map, patch_size=64, min_distance=10):
    """
    使用分水岭算法从概率图中分离粘连的结节，并提取patch。
    :param original_image: 原始灰度图 (用于提取patch)。
    :param prob_map: U-Net输出的原始概率图 (0-1之间)。
    :param patch_size: 提取的patch大小。
    :param min_distance: 分水岭算法中两个峰值的最小距离，用于控制分割的灵敏度。
    :return: 提取出的patch列表。
    """
    # 使用一个固定的阈值来确定前景区域
    binary_mask = prob_map > 0.5

    # 计算到背景的距离变换图
    distance = ndimage.distance_transform_edt(binary_mask)

    # 寻找距离变换图中的峰值作为标记点（markers）
    coords = peak_local_max(distance, min_distance=min_distance, labels=binary_mask)
    mask = np.zeros(distance.shape, dtype=bool)
    mask[tuple(coords.T)] = True
    markers, _ = ndimage.label(mask)

    # 应用分水岭算法
    labels = watershed(-distance, markers, mask=binary_mask)
    
    patches = []
    # 遍历所有被分水岭算法分离出的独立区域
    for region in measure.regionprops(labels):
        center_y, center_x = region.centroid
        min_row, min_col, max_row, max_col = region.bbox
        
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
        
        if patch.shape != (patch_size, patch_size):
            patch = transform.resize(patch, (patch_size, patch_size), anti_aliasing=True)
            
        patches.append({'patch': patch, 'bbox': (min_col, min_row, max_col, max_row)})
        
    return patches

def get_nodule_masks(ground_truth_json_path):
    """
    从权威的 ground_truth_inventory.json 文件加载真值掩码.
    返回一个以 SOP UID 为键，掩码数组为值的字典。
    """
    masks_dict = {}
    try:
        with open(ground_truth_json_path, 'r') as f:
            inventory = json.load(f)
        
        for item in tqdm(inventory, desc="加载真值掩码"):
            sop_uid = item['sop_uid']
            mask_path = item['mask_path']
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                masks_dict[sop_uid] = (mask > 0).astype(np.uint8)
            else:
                logger.warning(f"无法为SOP UID {sop_uid} 加载掩码: {mask_path}")

    except FileNotFoundError:
        logger.error(f"错误: 未找到真值清单文件: {ground_truth_json_path}")
    except Exception as e:
        logger.error(f"加载或解析真值清单文件时出错: {e}")
        
    logger.info(f"成功从 {ground_truth_json_path} 加载了 {len(masks_dict)} 个结节掩码")
    return masks_dict

def iou(boxA, boxB):
    """计算两个边界框的交并比 (Intersection over Union)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    
    iou_score = interArea / float(boxAArea + boxBArea - interArea)
    return iou_score

def create_dataset(model, dicom_root_dir, nodule_masks, output_dir, device, threshold=0.5, patch_size=64, img_size=(512, 512), iou_threshold=0.1):
    """运行U-Net，提取候选区，并生成CNN训练数据集."""
    model.eval()
    
    # 创建输出目录
    tp_dir = Path(output_dir) / "tp"
    fp_dir = Path(output_dir) / "fp"
    tp_dir.mkdir(parents=True, exist_ok=True)
    fp_dir.mkdir(parents=True, exist_ok=True)
    
    tp_count, fp_count = 0, 0
    
    logger.info(f"开始从根目录 {dicom_root_dir} 搜索所有DICOM文件...")
    dicom_files = list(Path(dicom_root_dir).rglob('*.dcm'))
    logger.info(f"共找到 {len(dicom_files)} 个DICOM文件")

    for dcm_file in tqdm(dicom_files, desc="生成CNN数据集"):
        try:
            dicom_data = pydicom.dcmread(dcm_file, force=True)
            sop_uid = dicom_data.SOPInstanceUID
            
            # 准备U-Net输入图像
            image_lung_window = apply_lung_window(dicom_data)
            if image_lung_window.shape[:2] != img_size:
                image_resized = cv2.resize(image_lung_window, img_size, interpolation=cv2.INTER_AREA)
            else:
                image_resized = image_lung_window
            
            input_tensor = torch.from_numpy(image_resized).float().unsqueeze(0).unsqueeze(0).to(device)
            
            # U-Net预测
            with torch.no_grad():
                output = model(input_tensor)
                pred_prob = output.squeeze().cpu().numpy()
                pred_mask = (pred_prob > threshold).astype(np.uint8)

            # 如果没有预测出任何东西，则跳过
            if np.sum(pred_mask) == 0:
                continue

            # 从预测掩码中提取所有候选区域的patch
            candidate_patches = extract_patches_with_watershed(image_resized, pred_prob, patch_size)
            
            # 获取真实掩码
            true_mask = nodule_masks.get(sop_uid)
            
            if true_mask is not None:
                if true_mask.shape[:2] != img_size:
                    true_mask = cv2.resize(true_mask, img_size, interpolation=cv2.INTER_NEAREST)
                
                # 获取真实掩码中所有结节的边界框
                true_labels = measure.label(true_mask)
                true_regions = measure.regionprops(true_labels)
                true_bboxes = [region.bbox for region in true_regions]
                 # (min_row, min_col, max_row, max_col) -> (min_col, min_row, max_col, max_row)
                true_bboxes = [(bbox[1], bbox[0], bbox[3], bbox[2]) for bbox in true_bboxes]

            else:
                true_bboxes = []

            # 标注每个候选patch是TP还是FP
            for i, cand in enumerate(candidate_patches):
                is_tp = False
                for true_box in true_bboxes:
                    if iou(cand['bbox'], true_box) > iou_threshold:
                        is_tp = True
                        break # 匹配到一个真结节即可
                
                # 将patch保存到对应目录
                # patch像素值在0-1之间，保存时需要转换到0-255
                patch_to_save = (cand['patch'] * 255).astype(np.uint8)
                
                if is_tp:
                    tp_count += 1
                    save_path = tp_dir / f"{sop_uid}_{i}.png"
                else:
                    fp_count += 1
                    save_path = fp_dir / f"{sop_uid}_{i}.png"
                
                cv2.imwrite(str(save_path), patch_to_save)

        except Exception as e:
            logger.error(f"处理DICOM文件 {dcm_file} 时出错: {e}", exc_info=True)
            
    logger.info(f"数据集生成完毕！")
    logger.info(f"真阳性 (TP) patches: {tp_count}")
    logger.info(f"假阳性 (FP) patches: {fp_count}")
    logger.info(f"数据保存在: {output_dir}")

def load_model(model_path, device):
    """加载U-Net模型."""
    try:
        state_dict = torch.load(model_path, map_location=device)
        is_bilinear = 'up1.up.weight' not in state_dict
        logger.info(f"检测到U-Net模型使用 {'bilinear=True' if is_bilinear else 'ConvTranspose (bilinear=False)'} 模式加载")
        
        model = UNet(n_channels=1, n_classes=1, bilinear=is_bilinear)
        model.load_state_dict(state_dict)
        model.to(device)
        logger.info(f"U-Net模型加载成功: {model_path}")
        return model
    except Exception as e:
        logger.error(f"加载模型文件 {model_path} 失败: {e}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description="为CNN分类器生成肺结节候选区域数据集")
    parser.add_argument("--model-path", type=str, default="../models/unet/model-best.pth", help="预训练的U-Net模型路径")
    parser.add_argument("--dicom-dir", type=str, default="../data/raw", help="包含DICOM数据的根目录")
    parser.add_argument("--ground-truth-json", type=str, default="../data/processed/ground_truth_dataset/ground_truth_inventory.json", help="权威真值清单JSON文件路径")
    parser.add_argument("--output-dir", type=str, default="../data/processed/cnn_classifier_dataset", help="保存生成的数据集的目录")
    parser.add_argument("--patch-size", type=int, default=64, help="提取的图像切片大小")
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")
    
    # 1. 加载U-Net模型
    unet_model = load_model(args.model_path, device)
    
    # 2. 从权威JSON文件加载真值掩码
    nodule_masks = get_nodule_masks(args.ground_truth_json)
    if not nodule_masks:
        logger.error("未能加载任何结节掩码，无法生成带标签的数据集。请先运行 extract_by_slice_union.py。")
        return
        
    # 3. 生成数据集
    create_dataset(unet_model, args.dicom_dir, nodule_masks, args.output_dir, device, patch_size=args.patch_size)

if __name__ == '__main__':
    main() 