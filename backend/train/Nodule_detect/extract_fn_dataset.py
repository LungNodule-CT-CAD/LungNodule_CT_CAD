"""
extract_fn_dataset.py
运行两阶段推断，自动把 FN 切片导出为微调数据集
"""
import argparse, cv2, numpy as np
from pathlib import Path
from tqdm import tqdm
import torch
from unet_model import UNet
from cnn_classifier_model import get_classifier_model

import pydicom, json, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 不能直接 import 以数字开头的模块名，因此在此处内嵌简化版 apply_lung_window
# (仅本脚本用得到)。

def apply_lung_window(dicom_data):
    """将 DICOM 切片转为 0-1 归一化的肺窗灰度图."""
    import numpy as _np
    pixel = dicom_data.pixel_array.astype(_np.float32)
    slope = getattr(dicom_data, 'RescaleSlope', 1)
    intercept = getattr(dicom_data, 'RescaleIntercept', 0)
    hu = pixel * slope + intercept
    wc, ww = -600, 1500
    w_min, w_max = wc - ww // 2, wc + ww // 2
    hu = _np.clip(hu, w_min, w_max)
    return (hu - w_min) / (w_max - w_min)

@torch.no_grad()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--unet-model", required=True)
    parser.add_argument("--cnn-model", required=True)
    parser.add_argument("--dicom-dir", required=True)
    parser.add_argument("--ground-truth-json", required=True)
    parser.add_argument("--save-dir", default="fn_dataset")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ---------- 加载模型 ---------- (根据权重决定 bilinear 模式)
    state_dict = torch.load(args.unet_model, map_location=device)
    is_bilinear = 'up1.up.weight' not in state_dict  # 与训练脚本保持一致的判定逻辑
    unet = UNet(1,1, bilinear=is_bilinear).to(device)
    unet.load_state_dict(state_dict)
    unet.eval()

    cnn = get_classifier_model().to(device)
    cnn.load_state_dict(torch.load(args.cnn_model, map_location=device))
    cnn.eval()

    # ---------- 读取真值 ----------
    with open(args.ground_truth_json) as f:
        inventory = {x["sop_uid"]: x["mask_path"] for x in json.load(f)}

    # ---------- 创建输出文件夹 ----------
    img_dir = Path(args.save_dir)/"images"
    msk_dir = Path(args.save_dir)/"masks"
    img_dir.mkdir(parents=True, exist_ok=True)
    msk_dir.mkdir(parents=True, exist_ok=True)

    dicom_files = list(Path(args.dicom_dir).rglob("*.dcm"))
    fn_cnt = 0
    for dcm in tqdm(dicom_files):
        d = pydicom.dcmread(dcm, force=True)
        sop = d.SOPInstanceUID
        if sop not in inventory:   # 没有真值的不参与
            continue

        # --------- Stage-1 预测 ----------
        lung = apply_lung_window(d)
        lung_resize = cv2.resize(lung, (512,512))
        ipt = torch.from_numpy(lung_resize).float()[None,None].to(device)
        pred_prob = unet(ipt).squeeze().cpu().numpy()
        pred_mask = (pred_prob>0.5).astype(np.uint8)

        # 如果 U-Net 已经漏检 → FN
        if pred_mask.sum()==0:
            # 保存
            fn_cnt += 1
            fn_name = f"{sop}.png"
            cv2.imwrite(str(img_dir/fn_name), (lung_resize*255).astype(np.uint8))

            gt = cv2.imread(inventory[sop], cv2.IMREAD_GRAYSCALE)
            if gt.shape[:2]!= (512,512):
                gt = cv2.resize(gt,(512,512), interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(str(msk_dir/fn_name), gt)

    logger.info(f"已导出 {fn_cnt} 张 FN 切片到 {args.save_dir}")

if __name__ == "__main__":
    main()