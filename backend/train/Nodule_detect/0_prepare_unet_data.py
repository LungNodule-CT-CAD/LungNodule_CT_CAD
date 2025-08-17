"""
生成对齐的图像-掩码对，用于U-Net训练

功能：同时对图像和掩码应用相同的数据增强，确保它们始终对齐
"""

import os
import glob
import numpy as np
import cv2
from tqdm import tqdm
import random
import pydicom
import xml.etree.ElementTree as ET
from scipy import ndimage as ndi
from collections import defaultdict
import argparse

# 设置最小有效区域大小（像素数）
MIN_NODULE_PIXELS = 9  # 舍弃小于25个像素的结节区域

def make_mask_from_polygon(edge_maps, width, height):
    """
    从多边形顶点创建掩码
    
    参数:
    edge_maps: 多边形顶点坐标列表 [(x1,y1), (x2,y2), ...]
    width, height: 输出掩码的宽度和高度
    
    返回:
    二值掩码，结节区域为255，其他区域为0
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    
    if len(edge_maps) > 2:  # 至少需要3个点才能形成一个多边形
        points = np.array(edge_maps, dtype=np.int32)
        cv2.fillPoly(mask, [points], 255)
    
    return mask


def is_valid_mask(mask):
    """
    判断掩码是否有效（面积需大于最小阈值）
    
    参数:
    mask: 掩码数组

    返回:
    布尔值，表示掩码是否有效
    """
    # 计算掩码中非零像素的数量
    pixel_count = np.count_nonzero(mask)
    
    # 如果像素数量小于阈值，则认为无效
    if pixel_count < MIN_NODULE_PIXELS:
        return False
        
    return True


def parse_nodule_xml(xml_file_path):
    """
    解析XML文件，提取结节信息
    
    参数:
    xml_file_path: XML文件路径
    
    返回:
    包含结节信息的字典列表，每个字典包含结节ID、Z位置、SOP_UID和边缘坐标
    """
    # 解析XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # 确定XML命名空间
    ns = {'nih': 'http://www.nih.gov'}
    
    # 存储所有结节信息的列表
    all_nodules = []
    
    # 遍历每个radiologist的readingSession
    for session_idx, session in enumerate(root.findall('.//nih:readingSession', ns)):
        # 遍历每个已确认的结节
        for nodule in session.findall('.//nih:unblindedReadNodule', ns):
            nodule_id = nodule.find('.//nih:noduleID', ns).text
            
            # 收集该结节的所有ROI信息
            rois = []
            for roi in nodule.findall('.//nih:roi', ns):
                # 获取Z位置和SOP_UID
                try:
                    z_pos = float(roi.find('.//nih:imageZposition', ns).text)
                    sop_uid = roi.find('.//nih:imageSOP_UID', ns).text
                    
                    # 收集边缘点坐标
                    edge_maps = []
                    for edge_map in roi.findall('.//nih:edgeMap', ns):
                        x = int(edge_map.find('.//nih:xCoord', ns).text)
                        y = int(edge_map.find('.//nih:yCoord', ns).text)
                        edge_maps.append((x, y))
                    
                    # 只有当边缘点坐标非空时才添加
                    if edge_maps:
                        # 计算中心点坐标
                        x_coords = [point[0] for point in edge_maps]
                        y_coords = [point[1] for point in edge_maps]
                        center_x = sum(x_coords) / len(x_coords)
                        center_y = sum(y_coords) / len(y_coords)
                        
                        # 计算半径（使用最远点到中心的距离）
                        distances = [np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2) for x, y in edge_maps]
                        radius = max(distances)
                        
                        # 添加到ROI列表
                        rois.append({
                            'z_position': z_pos,
                            'sop_uid': sop_uid,
                            'edge_maps': edge_maps,
                            'center_x': center_x,
                            'center_y': center_y,
                            'radius': radius,
                            'doctor_idx': session_idx
                        })
                except Exception as e:
                    print(f"处理结节 {nodule_id} 的ROI时出错: {e}")
            
            # 只有当ROI列表非空时才添加到结节列表
            if rois:
                all_nodules.append({
                    'nodule_id': nodule_id,
                    'rois': rois
                })
    
    return all_nodules


def merge_doctor_annotations(nodules, img_width, img_height):
    """
    合并多个医生对同一张CT图像的结节标注，取并集，并舍弃过小的区域
    
    参数:
    nodules: 结节信息列表，每个结节包含不同医生的标注
    img_width: 图像宽度
    img_height: 图像高度
    
    返回:
    字典，键为SOP_UID，值为该切片的合并掩码和有效结节列表
    """
    # 按切片分组
    slice_annotations = defaultdict(list)
    
    for nodule in nodules:
        for roi in nodule['rois']:
            slice_annotations[roi['sop_uid']].append({
                'nodule_id': nodule['nodule_id'],
                'edge_maps': roi['edge_maps'],
                'center_x': roi['center_x'],
                'center_y': roi['center_y'],
                'radius': roi['radius'],
                'doctor_idx': roi['doctor_idx']
            })
    
    # 对每个切片，合并不同医生的标注
    merged_annotations = {}
    
    for sop_uid, annotations in slice_annotations.items():
        # 创建空掩码
        merged_mask = np.zeros((img_height, img_width), dtype=np.uint8)
        valid_nodules = []
        
        # 按结节ID分组
        nodule_groups = defaultdict(list)
        for ann in annotations:
            nodule_groups[ann['nodule_id']].append(ann)
        
        # 处理每个结节
        for nodule_id, nodule_anns in nodule_groups.items():
            # 创建该结节的掩码（不同医生标注的并集）
            nodule_mask = np.zeros((img_height, img_width), dtype=np.uint8)
            
            for ann in nodule_anns:
                mask = make_mask_from_polygon(ann['edge_maps'], img_width, img_height)
                # 取并集
                nodule_mask = cv2.bitwise_or(nodule_mask, mask)
            
            # 检查结节区域是否有效（面积大于阈值）
            if is_valid_mask(nodule_mask):
                # 添加到合并掩码
                merged_mask = cv2.bitwise_or(merged_mask, nodule_mask)
                valid_nodules.append({
                    'nodule_id': nodule_id,
                    'mask': nodule_mask
                })
            else:
                pass
        
        # 只有当至少有一个有效结节时才添加
        if valid_nodules:
            merged_annotations[sop_uid] = {
                'mask': merged_mask,
                'nodules': valid_nodules
            }
    
    return merged_annotations


def map_sop_uid_to_file(dcm_dir):
    """
    创建SOP UID到文件名的映射
    
    参数:
    dcm_dir: 包含DICOM文件的目录
    
    返回:
    SOP UID到文件名的映射字典
    """
    sop_to_file = {}
    
    # 递归遍历所有目录
    for root, _, files in os.walk(dcm_dir):
        for file in files:
            if file.endswith('.dcm'):
                file_path = os.path.join(root, file)
                try:
                    dcm = pydicom.dcmread(file_path)
                    if hasattr(dcm, 'SOPInstanceUID'):
                        sop_to_file[dcm.SOPInstanceUID] = file_path
                except Exception as e:
                    print(f"无法读取文件 {file_path}: {e}")
    
    return sop_to_file


# 数据增强函数
def random_rotate(image, mask, min_angle=-20, max_angle=20):
    """
    同时对图像和掩码应用相同的随机旋转
    """
    angle = random.randint(min_angle, max_angle)
    center = (image.shape[1] // 2, image.shape[0] // 2)
    rot_matrix = cv2.getRotationMatrix2D(center, angle, scale=1.0)
    
    image_rotated = cv2.warpAffine(image, rot_matrix, image.shape[1::-1], flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    mask_rotated = cv2.warpAffine(mask, rot_matrix, mask.shape[1::-1], flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    
    return image_rotated, mask_rotated


def random_flip(image, mask):
    """
    同时对图像和掩码应用相同的随机翻转
    """
    # 随机选择翻转方式: 0=水平, 1=垂直, -1=水平和垂直
    flip_code = random.choice([0, 1, -1])
    
    image_flipped = cv2.flip(image, flip_code)
    mask_flipped = cv2.flip(mask, flip_code)
    
    return image_flipped, mask_flipped


def random_brightness_contrast(image, mask):
    """
    随机调整图像的亮度和对比度（仅对图像应用，掩码保持不变）
    """
    alpha = random.uniform(0.8, 1.2)  # 对比度
    beta = random.randint(-30, 30)    # 亮度
    
    image_adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    # 掩码保持不变
    return image_adjusted, mask


def random_zoom(image, mask, min_factor=0.9, max_factor=1.1):
    """
    同时对图像和掩码应用相同的随机缩放
    """
    zoom_factor = random.uniform(min_factor, max_factor)
    
    # 计算新的尺寸
    h, w = image.shape[:2]
    new_h = int(h * zoom_factor)
    new_w = int(w * zoom_factor)
    
    # 应用缩放
    image_zoomed = cv2.resize(image, (new_w, new_h))
    mask_zoomed = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
    
    # 如果缩放后的图像大于原始图像，裁剪中心区域
    if zoom_factor > 1:
        start_h = (new_h - h) // 2
        start_w = (new_w - w) // 2
        image_zoomed = image_zoomed[start_h:start_h+h, start_w:start_w+w]
        mask_zoomed = mask_zoomed[start_h:start_h+h, start_w:start_w+w]
    # 如果缩放后的图像小于原始图像，填充到原始大小
    elif zoom_factor < 1:
        pad_h = (h - new_h) // 2
        pad_w = (w - new_w) // 2
        
        image_zoomed = cv2.copyMakeBorder(image_zoomed, pad_h, h-new_h-pad_h, pad_w, w-new_w-pad_w, cv2.BORDER_CONSTANT)
        mask_zoomed = cv2.copyMakeBorder(mask_zoomed, pad_h, h-new_h-pad_h, pad_w, w-new_w-pad_w, cv2.BORDER_CONSTANT)
    
    return image_zoomed, mask_zoomed


def resize_pair(image, mask, target_size):
    """
    将图像和掩码调整到目标大小
    """
    if isinstance(target_size, int):
        target_size = (target_size, target_size)
    
    image_resized = cv2.resize(image, target_size)
    mask_resized = cv2.resize(mask, target_size, interpolation=cv2.INTER_NEAREST)
    
    return image_resized, mask_resized


def augment_pair(image, mask, augmentation_count=1, target_size=None):
    """
    对图像和掩码应用相同的一系列增强操作
    
    参数:
    image: 原始图像
    mask: 对应的掩码
    augmentation_count: 要生成的增强版本数量
    target_size: 目标大小（如果需要调整大小）
    
    返回:
    增强后的图像和掩码对列表
    """
    augmented_pairs = []
    
    # for i in range(augmentation_count):
        # 复制原始图像和掩码
    img_aug = image.copy()
    mask_aug = mask.copy()
    
    img_aug, mask_aug = random_flip(img_aug, mask_aug)
    # 如果需要，调整大小
    if target_size:
        img_aug, mask_aug = resize_pair(img_aug, mask_aug, target_size)
        
    augmented_pairs.append((img_aug, mask_aug))
    
    return augmented_pairs


def process_patient_data(patient_dir, output_dir, target_size=None, augmentation_count=1):
    """
    处理单个患者的数据，生成对齐的图像-掩码对
    
    参数:
    patient_dir: 患者数据目录
    output_dir: 输出目录
    target_size: 目标图像大小
    augmentation_count: 每对图像掩码生成的增强版本数
    """
    # 确保输出目录存在
    images_dir = os.path.join(output_dir, 'images')
    masks_dir = os.path.join(output_dir, 'masks')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(masks_dir, exist_ok=True)
    
    patient_id = os.path.basename(patient_dir)
    
    # 查找XML文件
    xml_files = []
    for root, _, files in os.walk(patient_dir):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    if not xml_files:
        print(f"警告: 未找到XML标注文件，跳过患者 {patient_id}")
        return 0
    
    # 创建SOP UID到文件名的映射
    sop_to_file = map_sop_uid_to_file(patient_dir)
    
    # 处理XML文件，获取所有结节信息
    all_nodules = []
    for xml_file in xml_files:
        print(f"正在解析XML文件: {os.path.basename(xml_file)}")
        try:
            # 解析XML文件，提取结节信息
            nodules = parse_nodule_xml(xml_file)
            all_nodules.extend(nodules)
        except Exception as e:
            print(f"解析XML文件 {xml_file} 时出错: {e}")
    
    # 统计处理的图像对数量
    total_pairs = 0
    
    # 读取一个样例DICOM文件以获取图像尺寸
    sample_dcm_path = None
    for uid, path in sop_to_file.items():
        sample_dcm_path = path
        break
    
    if sample_dcm_path is None:
        print(f"错误: 未找到任何DICOM文件，跳过患者 {patient_id}")
        return 0
    
    try:
        sample_dcm = pydicom.dcmread(sample_dcm_path)
        img_width = sample_dcm.pixel_array.shape[1]
        img_height = sample_dcm.pixel_array.shape[0]
    except Exception as e:
        print(f"读取样例DICOM文件出错: {e}")
        # 使用默认尺寸
        img_width = 512
        img_height = 512
    
    # 合并多个医生的标注，并舍弃过小的区域
    print(f"正在合并医生标注...")
    merged_annotations = merge_doctor_annotations(all_nodules, img_width, img_height)
    print(f"共找到 {len(merged_annotations)} 个有效CT切片")
    
    # 处理每个切片
    for sop_uid, annotation in merged_annotations.items():
        # 查找对应的DICOM文件
        if sop_uid in sop_to_file:
            dcm_path = sop_to_file[sop_uid]
            
            try:
                # 读取DICOM文件
                dcm = pydicom.dcmread(dcm_path)
                pixel_array = dcm.pixel_array
                
                # 应用窗宽窗位（肺窗）
                window_center = -600
                window_width = 1500
                min_value = window_center - window_width // 2
                max_value = window_center + window_width // 2
                
                # 转换为浮点数，应用窗宽窗位
                image = pixel_array.astype(np.float32)
                
                # 如果有Rescale Slope和Intercept，应用它们
                if hasattr(dcm, 'RescaleSlope') and hasattr(dcm, 'RescaleIntercept'):
                    image = image * dcm.RescaleSlope + dcm.RescaleIntercept
                    
                # 应用窗宽窗位
                image = np.clip(image, min_value, max_value)
                
                # 归一化到[0, 255]
                image = ((image - min_value) / (max_value - min_value) * 255).astype(np.uint8)
                
                # 获取合并后的掩码
                mask = annotation['mask']
                
                # 确保掩码有效
                if not is_valid_mask(mask):
                    print(f"警告: 切片 {os.path.basename(dcm_path)} 的合并掩码无效，跳过")
                    continue
                
                # 生成图像-掩码对的增强版本
                augmented_pairs = augment_pair(image, mask, augmentation_count, target_size)
                
                # 保存原始和增强后的图像-掩码对
                # 首先保存原始图像和掩码
                base_name = f"{patient_id}_slice{os.path.splitext(os.path.basename(dcm_path))[0]}"
                
                # 如果需要调整大小
                if target_size:
                    image, mask = resize_pair(image, mask, target_size)
                    
                # 保存原始图像和掩码
                cv2.imwrite(os.path.join(images_dir, f"{base_name}_orig.png"), image)
                cv2.imwrite(os.path.join(masks_dir, f"{base_name}_orig_mask.png"), mask)
                total_pairs += 1
                
                # 保存增强后的图像和掩码
                for i, (aug_image, aug_mask) in enumerate(augmented_pairs):
                    aug_name = f"{base_name}_aug{i+1}"
                    cv2.imwrite(os.path.join(images_dir, f"{aug_name}.png"), aug_image)
                    cv2.imwrite(os.path.join(masks_dir, f"{aug_name}_mask.png"), aug_mask)
                    total_pairs += 1
                    
            except Exception as e:
                print(f"处理DICOM文件 {dcm_path} 时出错: {e}")
        else:
            print(f"警告: 未找到SOP UID {sop_uid} 对应的DICOM文件")
    
    return total_pairs


def batch_process_patients(base_dir, output_dir, target_size=None, augmentation_count=1):
    """
    批量处理多个患者的数据
    
    参数:
    base_dir: 包含患者数据的基础目录
    output_dir: 输出目录
    target_size: 目标图像大小
    augmentation_count: 每对图像掩码生成的增强版本数
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 统计处理的患者和图像对数量
    processed_patients = 0
    total_pairs = 0
    
    # 遍历基础目录查找患者文件夹
    for item in os.listdir(base_dir):
        patient_dir = os.path.join(base_dir, item)
        
        # 检查是否是目录且是患者ID格式
        if os.path.isdir(patient_dir) and item.startswith("LIDC-IDRI-"):
            print(f"\n============ 处理患者: {item} ============")
            
            # 处理患者数据
            try:
                pairs = process_patient_data(patient_dir, output_dir, target_size, augmentation_count)
                
                if pairs > 0:
                    processed_patients += 1
                    total_pairs += pairs
                    print(f"✓ 患者 {item}: 成功生成 {pairs} 对图像-掩码数据")
                else:
                    print(f"✗ 患者 {item}: 未能生成数据")
                    
            except Exception as e:
                print(f"✗ 处理患者 {item} 时出错: {e}")
    
    # 打印处理结果统计
    print(f"\n数据处理完成!")
    print(f"成功处理: {processed_patients} 个患者")
    print(f"共生成: {total_pairs} 对图像-掩码数据")
    
    # 创建一个数据划分文件，将数据集分为训练集和验证集
    if total_pairs > 0:
        # 获取所有图像文件
        images = glob.glob(os.path.join(output_dir, 'images', '*.png'))
        # 随机打乱
        random.shuffle(images)
        
        # 分割为训练集和验证集 (80% 训练, 20% 验证)
        split_idx = int(len(images) * 0.8)
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        # 创建对应的掩码文件路径
        train_masks = [os.path.join(output_dir, 'masks', os.path.basename(img).replace('.png', '_mask.png')) for img in train_images]
        val_masks = [os.path.join(output_dir, 'masks', os.path.basename(img).replace('.png', '_mask.png')) for img in val_images]
        
        # 写入训练集和验证集文件
        with open(os.path.join(output_dir, 'train.txt'), 'w') as f:
            for img, mask in zip(train_images, train_masks):
                f.write(f"{os.path.basename(img)},{os.path.basename(mask)}\n")
                
        with open(os.path.join(output_dir, 'val.txt'), 'w') as f:
            for img, mask in zip(val_images, val_masks):
                f.write(f"{os.path.basename(img)},{os.path.basename(mask)}\n")
                
        print(f"已创建数据集划分文件:")
        print(f"- 训练集: {len(train_images)} 对")
        print(f"- 验证集: {len(val_images)} 对")
    
    return processed_patients, total_pairs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="从LIDC-IDRI数据集中生成对齐的图像-掩码对，用于U-Net训练。")
    parser.add_argument('--data-dir', type=str, default='./data/raw',
                        help='包含LIDC-IDRI DICOM和XML文件的根目录。')
    parser.add_argument('--output-dir', type=str, default='./data/processed/unet_training_data',
                        help='保存生成的PNG图像、掩码和文件列表的目录。')
    parser.add_argument('--target-size', type=int, default=512,
                        help='所有输出图像和掩码的目标尺寸 (方形)。')
    parser.add_argument('--augmentation-count', type=int, default=1,
                        help='为每个原始图像-掩码对生成的增强版本数量。')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"数据目录: {args.data_dir}")
    print(f"输出目录: {args.output_dir}")
    print(f"目标尺寸: {args.target_size}x{args.target_size}")
    print(f"增强数量: {args.augmentation_count}")
    
    # 批量处理数据
    print(f"开始生成对齐的图像-掩码数据...")
    processed, total = batch_process_patients(
        args.data_dir, 
        args.output_dir, 
        args.target_size, 
        args.augmentation_count
    )
    
    if processed > 0:
        print(f"数据生成完成! 已为 {processed} 个患者生成共 {total} 对图像-掩码数据")
        print(f"输出位置: {args.output_dir}")
    else:
        print("未能生成任何数据，请检查输入数据") 