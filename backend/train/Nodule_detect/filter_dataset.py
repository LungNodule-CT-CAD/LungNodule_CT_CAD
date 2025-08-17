import cv2
import numpy as np
from pathlib import Path
import argparse
from tqdm import tqdm
import shutil
import os

def filter_dataset(input_dir, output_dir, min_pixels=100, min_region_size=50):
    """
    过滤数据集，只保留掩码中结节区域像素数大于阈值的图像
    
    参数:
    - input_dir: 输入数据集目录，应包含images和masks子目录
    - output_dir: 输出目录，将创建images和masks子目录
    - min_pixels: 掩码中白色像素的最小数量
    - min_region_size: 单个连通区域的最小像素数，小于此值的区域将被过滤掉
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # 确保输入目录存在
    if not input_path.exists() or not (input_path / "images").exists() or not (input_path / "masks").exists():
        raise ValueError(f"输入目录 {input_dir} 不存在或缺少images/masks子目录")
    
    # 创建输出目录
    images_out_dir = output_path / "images"
    masks_out_dir = output_path / "masks"
    
    if output_path.exists():
        shutil.rmtree(output_path)  # 清除之前的输出
    
    images_out_dir.mkdir(parents=True)
    masks_out_dir.mkdir(parents=True)
    
    # 获取所有掩码文件
    mask_files = list((input_path / "masks").glob("*.png"))
    total_files = len(mask_files)
    
    stats = {
        "total": total_files,
        "filtered_small_nodules": 0,
        "filtered_small_regions": 0,
        "kept": 0
    }
    
    print(f"处理中，总共有 {total_files} 个文件...")
    
    for mask_file in tqdm(mask_files, desc="过滤数据集"):
        # 读取掩码
        mask = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
        
        # 检查掩码总像素数
        white_pixels = np.sum(mask > 0)
        
        if white_pixels < min_pixels:
            stats["filtered_small_nodules"] += 1
            continue
        
        # 过滤小区域
        if min_region_size > 0:
            filtered_mask = np.zeros_like(mask)
            # 找到所有连通区域
            num_labels, labels = cv2.connectedComponents(mask)
            
            has_valid_region = False
            # 对于每个区域，如果大小足够则保留
            for label in range(1, num_labels):  # 跳过背景标签0
                region_mask = (labels == label).astype(np.uint8) * 255
                region_size = np.sum(region_mask > 0)
                
                if region_size >= min_region_size:
                    # 将此区域添加到过滤后的掩码中
                    filtered_mask = cv2.bitwise_or(filtered_mask, region_mask)
                    has_valid_region = True
            
            if not has_valid_region:
                stats["filtered_small_regions"] += 1
                continue
            
            # 使用过滤后的掩码
            mask = filtered_mask
        
        # 获取对应的图像文件名和路径
        file_stem = mask_file.stem
        image_file = input_path / "images" / f"{file_stem}.png"
        
        # 如果图像文件存在，则复制
        if image_file.exists():
            # 读取原始图像
            image = cv2.imread(str(image_file))
            
            # 保存过滤后的图像和掩码
            cv2.imwrite(str(masks_out_dir / f"{file_stem}.png"), mask)
            cv2.imwrite(str(images_out_dir / f"{file_stem}.png"), image)
            
            stats["kept"] += 1
        else:
            print(f"警告：找不到对应的图像文件 {image_file}")
    
    # 输出统计信息
    print("\n数据集过滤完成！统计信息:")
    print(f"总文件数: {stats['total']}")
    print(f"因结节总像素数太小而过滤的文件: {stats['filtered_small_nodules']}")
    print(f"因所有连通区域都太小而过滤的文件: {stats['filtered_small_regions']}")
    print(f"保留的文件数: {stats['kept']} ({stats['kept']/stats['total']*100:.2f}%)")
    print(f"已保存到: {output_path}")
    
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="过滤数据集，只保留掩码区域像素数大于阈值的图像")
    parser.add_argument("--input", "-i", type=str, default="./LIDC_processed", help="输入数据集目录，应包含images和masks子目录")
    parser.add_argument("--output", "-o", type=str, default="./LIDC_filtered", help="输出目录")
    parser.add_argument("--min_pixels", "-p", type=int, default=100, help="掩码中白色像素的最小总数量")
    parser.add_argument("--min_region", "-r", type=int, default=50, help="单个连通区域的最小像素数，设为0表示不过滤小区域")
    
    args = parser.parse_args()
    
    filter_dataset(args.input, args.output, args.min_pixels, args.min_region) 