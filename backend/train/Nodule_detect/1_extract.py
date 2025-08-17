import os
import shutil
from lxml import etree
from pathlib import Path
from tqdm import tqdm
import logging
import pydicom
import cv2
import numpy as np
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("extract_slices_union.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def apply_lung_window(dicom_data):
    """对DICOM应用肺窗"""
    # 获取像素数据
    pixel_data = dicom_data.pixel_array.astype(np.float32)
    
    # 获取比例和偏移 (用于转换为HU单位)
    slope = getattr(dicom_data, 'RescaleSlope', 1)
    intercept = getattr(dicom_data, 'RescaleIntercept', 0)
    
    # 转换为HU单位
    hu_image = pixel_data * slope + intercept
    
    # 应用肺窗
    window_center = -600  # 肺窗中心
    window_width = 1500   # 肺窗宽度
    
    window_min = window_center - window_width // 2
    window_max = window_center + window_width // 2
    
    windowed_image = np.clip(hu_image, window_min, window_max)
    
    # 归一化到0-255用于保存
    normalized = ((windowed_image - window_min) / (window_max - window_min) * 255).astype(np.uint8)
    
    return normalized

def get_nodule_slices_union(xml_files, namespace, min_roi_points=5):
    """
    从XML文件中提取包含结节的切片信息，并按照SOP UID组织
    将所有医生的标注合并为一个并集
    
    返回:
    包含结节的切片的SOP实例UID字典，键为SOP UID，值为所有医生标注的结节坐标列表
    """
    nodule_slices = {}
    
    # 遍历所有XML文件
    for xml_path in xml_files:
        try:
            tree = etree.parse(str(xml_path))
            
            # 获取所有阅片会话(每个会话代表一位医生的标注)
            reading_sessions = tree.xpath('//ns:readingSession', namespaces={'ns': namespace})
            
            # 处理每位医生的标注
            for session_idx, session in enumerate(reading_sessions):
                # 查找此医生标注的所有结节
                nodules = session.xpath('.//ns:unblindedReadNodule', namespaces={'ns': namespace})
                
                # 处理每个结节j
                for nodule_idx, nodule in enumerate(nodules):
                    nodule_id = f"rad{session_idx+1}_nod{nodule_idx+1}"
                    
                    # 查找此结节的所有ROI(每个ROI对应一个切片上的标注)
                    rois = nodule.xpath('.//ns:roi', namespaces={'ns': namespace})
                    
                    # 处理每个ROI
                    for roi in rois:
                        # 获取切片的SOP实例UID
                        sop_uid_elem = roi.find('ns:imageSOP_UID', namespaces={'ns': namespace})
                        if sop_uid_elem is None or not sop_uid_elem.text:
                            continue
                        
                        sop_uid = sop_uid_elem.text.strip()
                        
                        # 获取ROI边界点
                        edge_maps = roi.xpath('.//ns:edgeMap', namespaces={'ns': namespace})
                        roi_points = len(edge_maps)
                        
                        # 只保留边界点足够多的标注
                        if roi_points < min_roi_points:
                            continue
                        
                        # 获取此ROI的所有坐标点
                        coords = []
                        for point in edge_maps:
                            x = point.find('ns:xCoord', namespaces={'ns': namespace})
                            y = point.find('ns:yCoord', namespaces={'ns': namespace})
                            if x is not None and y is not None:
                                coords.append((int(y.text), int(x.text)))  # (row, col)
                        
                        # 将坐标加入到对应的切片中
                        if sop_uid not in nodule_slices:
                            nodule_slices[sop_uid] = {
                                'coords': [],
                                'radiologist_count': 0,
                                'nodule_count': 0
                            }
                        
                        if coords and len(coords) > 2:  # 至少3个点才能形成有效多边形
                            nodule_slices[sop_uid]['coords'].append(coords)
                            nodule_slices[sop_uid]['nodule_count'] += 1
            
            # 更新每个切片被多少位医生标注的计数
            for sop_uid in nodule_slices:
                nodule_slices[sop_uid]['radiologist_count'] = len(reading_sessions)
                        
        except Exception as e:
            logger.error(f"解析XML文件 {xml_path} 出错: {e}")
    
    return nodule_slices

def extract_nodule_slices_union(root_path, output_path, min_roi_points=5):
    """
    提取包含结节标注的切片信息，并将所有数据保存到一个权威的JSON清单文件中。
    同时，将合并后的掩码保存为独立的PNG文件。
    """
    namespace = "http://www.nih.gov"
    
    # 准备输出目录
    mask_output = output_path / "masks_unified"
    if mask_output.exists():
        shutil.rmtree(mask_output)
    mask_output.mkdir(parents=True)
    
    logger.info(f"开始扫描 {root_path} 查找包含结节的切片...")
    
    ground_truth_inventory = []
    
    patient_dirs = sorted([d for d in root_path.iterdir() if d.is_dir()])
    
    for patient_dir in tqdm(patient_dirs, desc="处理患者数据"):
        study_dirs = [d for d in patient_dir.rglob('*') if d.is_dir() and any(f.suffix == '.dcm' for f in d.iterdir())]
        
        for study_dir in study_dirs:
            xml_files = list(study_dir.glob('*.xml'))
            if not xml_files:
                continue
            
            nodule_slices_info = get_nodule_slices_union(xml_files, namespace, min_roi_points)
            if not nodule_slices_info:
                continue
            
            for dcm_file in study_dir.glob('*.dcm'):
                try:
                    dicom_data = pydicom.dcmread(str(dcm_file), stop_before_pixels=True)
                    sop_uid = dicom_data.SOPInstanceUID.strip()
                    
                    if sop_uid in nodule_slices_info:
                        # 创建掩码图像
                        img_shape = (dicom_data.Rows, dicom_data.Columns)
                        mask = np.zeros(img_shape, dtype=np.uint8)
                        
                        for coords in nodule_slices_info[sop_uid]['coords']:
                            if len(coords) > 2:
                                points = np.array(coords, dtype=np.int32)
                                # pydicom的坐标是(col, row), cv2是(x, y), 需要转换
                                points = points[:, [1, 0]]
                                cv2.fillPoly(mask, [points], 255)
                        
                        # 保存掩码文件，使用唯一的SOP UID命名
                        mask_filename = f"{sop_uid}.png"
                        mask_filepath = mask_output / mask_filename
                        cv2.imwrite(str(mask_filepath), mask)
                        
                        # 添加到清单中
                        ground_truth_inventory.append({
                            'patient_id': patient_dir.name,
                            'sop_uid': sop_uid,
                            'original_dicom_path': str(dcm_file.resolve()),
                            'mask_path': str(mask_filepath.resolve())
                        })
                        
                except Exception as e:
                    logger.error(f"处理 {dcm_file} 时出错: {e}")

    # 保存权威的JSON清单文件
    output_json_path = output_path / "ground_truth_inventory.json"
    with open(output_json_path, 'w') as f:
        json.dump(ground_truth_inventory, f, indent=4)
        
    logger.info("\n提取完成！")
    logger.info(f"共找到 {len(ground_truth_inventory)} 个包含结节的真值切片。")
    logger.info(f"统一的掩码文件保存在: {mask_output}")
    logger.info(f"权威真值清单文件保存在: {output_json_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="从LIDC-IDRI数据集中提取结节信息并生成权威的JSON清单")
    parser.add_argument('--input', '-i', type=str, default='/root/Lung/data',
                      help='输入数据集根目录 (e.g., ./data/raw)')
    parser.add_argument('--output', '-o', type=str, default='/root/Lung/ver2/Nodule-Detec/U-net/data/processed/ground_truth_dataset',
                      help='输出目录')
    parser.add_argument('--min_roi_points', '-m', type=int, default=10,
                      help='结节边界点的最小数量')
    
    args = parser.parse_args()
    
    data_root = Path(args.input)
    output_root = Path(args.output)
    
    # 确保输出目录存在
    output_root.mkdir(exist_ok=True)
    
    extract_nodule_slices_union(data_root, output_root, args.min_roi_points) 