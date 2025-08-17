"""finetune_unet.py
中文注释版 U-Net 微调脚本 (专用 FN 数据)
-------------------------------------------------
• 依赖: PyTorch, scikit-image, tqdm
• 数据要求: --fn-data-dir 内包含 images/ 与 masks/ 两个子文件夹,
  文件名一一对应。
• 保存: 在 --output-path 处保存验证集 Dice 最佳的模型权重。
"""
import argparse
from pathlib import Path
import random
import os
import numpy as np
import cv2
from tqdm import tqdm

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split

from sklearn.metrics import precision_recall_fscore_support

from unet_model import UNet  # 已存在的网络定义

# ------------------------- 数据集 -------------------------
class FNDataset(Dataset):
    def __init__(self, data_dir: str, img_size=(512, 512)):
        self.img_dir = Path(data_dir) / 'images'
        self.mask_dir = Path(data_dir) / 'masks'
        self.img_size = img_size
        self.image_paths = sorted(list(self.img_dir.glob('*.png')) + list(self.img_dir.glob('*.jpg')))
        assert len(self.image_paths) > 0, f"在 {self.img_dir} 未找到图片！"

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        mask_path = Path(str(img_path).replace(str(self.img_dir), str(self.mask_dir)))
        # 读取灰度图
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        # 尺寸调整
        if img.shape[:2] != self.img_size:
            img = cv2.resize(img, self.img_size)
        if mask.shape[:2] != self.img_size:
            mask = cv2.resize(mask, self.img_size, interpolation=cv2.INTER_NEAREST)
        # 归一化
        img = img / 255.0
        mask = (mask > 0.5).astype(np.float32)
        # 转 Tensor
        img = torch.from_numpy(img).float().unsqueeze(0)  # (1,H,W)
        mask = torch.from_numpy(mask).float().unsqueeze(0)
        return img, mask

# ------------------------ 损失函数 ------------------------
def dice_coeff(pred, target, eps=1e-6):
    pred_f = pred.view(-1)
    tgt_f = target.view(-1)
    inter = (pred_f * tgt_f).sum()
    return (2*inter + eps) / (pred_f.sum() + tgt_f.sum() + eps)

class DiceBCELoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.bce = nn.BCELoss()

    def forward(self, pred, target):
        return self.bce(pred, target) + (1 - dice_coeff(pred, target))

# ----------------------- 训练与验证 -----------------------
@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    total_loss, total_dice = 0, 0
    criterion = DiceBCELoss()
    for imgs, masks in loader:
        imgs, masks = imgs.to(device), masks.to(device)
        preds = model(imgs)
        loss = criterion(preds, masks)
        total_loss += loss.item() * imgs.size(0)
        total_dice += dice_coeff(preds, masks).item() * imgs.size(0)
    n = len(loader.dataset)
    return total_loss / n, total_dice / n

def train_one_epoch(model, loader, optimizer, scaler, device):
    model.train()
    criterion = DiceBCELoss()
    total_loss = 0
    for imgs, masks in tqdm(loader, leave=False):
        imgs, masks = imgs.to(device), masks.to(device)
        optimizer.zero_grad()
        with torch.cuda.amp.autocast(enabled=False):  # BCE 与 AMP 不兼容
            preds = model(imgs)
            loss = criterion(preds, masks)
        if scaler is not None:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
        total_loss += loss.item() * imgs.size(0)
    return total_loss / len(loader.dataset)

# ---------------------------- 主函数 ----------------------------

def main():
    parser = argparse.ArgumentParser(description='U-Net Fine-tune on FN patches')
    parser.add_argument('--fn-data-dir', type=str, required=True,default='../data/processed/fn_dataset',
                        help='包含 images/ 与 masks/ 的FN数据目录')
    parser.add_argument('--pretrained-model', type=str, required=True,
                        help='已训练U-Net权重 (.pth)')
    parser.add_argument('--output-path', type=str, default='../models/unet/model-finetuned.pth')
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--lr', type=float, default=1e-5)
    parser.add_argument('--val-split', type=float, default=0.2)
    parser.add_argument('--freeze-encoder', action='store_true', help='是否冻结编码器层')
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    # 数据集
    dataset = FNDataset(args.fn_data_dir)
    val_len = int(len(dataset) * args.val_split)
    train_len = len(dataset) - val_len
    train_set, val_set = random_split(dataset, [train_len, val_len],
                                      generator=torch.Generator().manual_seed(42))
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)

    # -------- 根据权重判定 bilinear 设置，防止尺寸不匹配 --------
    state = torch.load(args.pretrained_model, map_location=device)
    is_bilinear = 'up1.up.weight' not in state  # 与原训练脚本同一判定逻辑
    model = UNet(n_channels=1, n_classes=1, bilinear=is_bilinear).to(device)
    model.load_state_dict(state)
    print(f'加载预训练权重: {args.pretrained_model} | bilinear={is_bilinear}')

    if args.freeze_encoder:
        for name, param in model.named_parameters():
            if name.startswith(('inc', 'down1', 'down2', 'down3', 'down4')):
                param.requires_grad = False
        print('已冻结编码器层，仅微调解码器')

    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=args.lr)
    scaler = None  # 禁用 AMP，避免 BCE 与 autocast 冲突

    best_dice = 0
    for epoch in range(1, args.epochs+1):
        train_loss = train_one_epoch(model, train_loader, optimizer, scaler, device)
        val_loss, val_dice = evaluate(model, val_loader, device)

        print(f'Epoch {epoch}/{args.epochs} | Train Loss {train_loss:.4f} | '
              f'Val Loss {val_loss:.4f} | Val Dice {val_dice:.4f}')

        # 保存最佳模型
        if val_dice > best_dice:
            best_dice = val_dice
            Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), args.output_path)
            print(f'>> 保存新最佳模型: Dice={best_dice:.4f} -> {args.output_path}')

    print('微调结束，最佳验证Dice:', best_dice)


if __name__ == '__main__':
    main() 