"""
U-Net 模型训练脚本 (PyTorch版本)

使用生成的对齐图像-掩码数据训练 U-Net 模型进行肺结节分割
"""

import os
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import random
from datetime import datetime
from tqdm import tqdm
import gc
from pathlib import Path

# 导入混合精度训练模块
from torch.cuda.amp import autocast, GradScaler


# 设置设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")
# 定义U-Net模型
class DoubleConv(nn.Module):
    """(卷积 => 标准化 => ReLU) * 2"""
    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)


class Down(nn.Module):
    """下采样，然后double conv"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        return self.maxpool_conv(x)


class Up(nn.Module):
    """上采样，然后double conv"""
    def __init__(self, in_channels, out_channels, bilinear=True):
        super().__init__()

        # 如果使用双线性插值，则使用普通卷积
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
        # 否则使用转置卷积
        else:
            self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        # 调整x1的尺寸以匹配x2
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]

        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2,
                        diffY // 2, diffY - diffY // 2])
        
        # 连接特征图
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutConv(nn.Module):
    """输出卷积"""
    def __init__(self, in_channels, out_channels):
        super(OutConv, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        return self.conv(x)


class UNet(nn.Module):
    """完整的U-Net架构"""
    def __init__(self, n_channels=1, n_classes=1, bilinear=False):
        super(UNet, self).__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        # 编码器路径
        self.inc = DoubleConv(n_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        factor = 2 if bilinear else 1
        self.down4 = Down(512, 1024 // factor)
        
        # 解码器路径
        self.up1 = Up(1024, 512 // factor, bilinear)
        self.up2 = Up(512, 256 // factor, bilinear)
        self.up3 = Up(256, 128 // factor, bilinear)
        self.up4 = Up(128, 64, bilinear)
        self.outc = OutConv(64, n_classes)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return torch.sigmoid(logits)


class FileBasedNoduleDataset(Dataset):
    """基于文件的肺结节数据集，实现按需从磁盘读取数据"""
    def __init__(self, image_paths, mask_paths, img_size=(512, 512), transform=None):
        self.image_paths = image_paths  # 图像文件路径列表
        self.mask_paths = mask_paths    # 掩码文件路径列表
        self.img_size = img_size        # 图像大小
        self.transform = transform      # 数据转换
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        # 读取图像
        img = cv2.imread(self.image_paths[idx], cv2.IMREAD_GRAYSCALE)
        mask = cv2.imread(self.mask_paths[idx], cv2.IMREAD_GRAYSCALE)
        
        # 调整大小
        if img.shape[:2] != self.img_size:
            img = cv2.resize(img, self.img_size)
        if mask.shape[:2] != self.img_size:
            mask = cv2.resize(mask, self.img_size, interpolation=cv2.INTER_NEAREST)
        
        # 归一化和二值化
        img = img / 255.0
        mask = (mask > 0.5).astype(np.float32)
        
        # 转换为张量
        img = torch.from_numpy(img).float().unsqueeze(0)
        mask = torch.from_numpy(mask).float().unsqueeze(0)
        
        # 应用变换
        if self.transform:
            img = self.transform(img)
            mask = self.transform(mask)
            
        return img, mask


# Dice系数计算
def dice_coeff(pred, target, epsilon=1e-6):
    """
    计算Dice系数
    pred: 预测的二值掩码 (B, C, H, W)
    target: 目标二值掩码 (B, C, H, W)
    epsilon: 防止除零错误的小值
    """
    # 将预测值和目标值展平
    pred_flat = pred.view(-1)
    target_flat = target.view(-1)
    
    # 计算交集
    intersection = (pred_flat * target_flat).sum()
    
    # 计算Dice系数
    return (2. * intersection + epsilon) / (pred_flat.sum() + target_flat.sum() + epsilon)


def dice_loss(pred, target, epsilon=1e-6):
    """
    基于Dice系数的损失函数
    """
    return 1 - dice_coeff(pred, target, epsilon)


class DiceBCELoss(nn.Module):
    """结合二元交叉熵和Dice损失"""
    def __init__(self):
        super(DiceBCELoss, self).__init__()
        self.bce = nn.BCELoss()

    def forward(self, pred, target):
        bce_loss = self.bce(pred, target)
        dice_loss_val = dice_loss(pred, target)
        return bce_loss + dice_loss_val


def get_data_paths(data_dir, file_list_path):
    """从文件列表（如 train_files.txt）中读取图像和掩码的路径"""
    image_paths = []
    mask_paths = []
    
    img_dir = Path(data_dir) / 'images'
    mask_dir = Path(data_dir) / 'masks'
    
    with open(file_list_path, 'r') as f:
        for line in f.readlines():
            img_name, mask_name = line.strip().split(',')
            image_paths.append(str(img_dir / img_name))
            mask_paths.append(str(mask_dir / mask_name))
            
    return image_paths, mask_paths


def plot_training_results(train_losses, val_losses, train_dices, val_dices, save_dir):
    """
    绘制训练结果并保存图表
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # 创建子目录保存可视化图像
    plots_dir = os.path.join(save_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    # 创建图表 - Loss曲线
    plt.figure(figsize=(12, 8))
    
    # 绘制损失
    plt.subplot(2, 2, 1)
    epochs = range(1, len(train_losses) + 1)
    plt.plot(epochs, train_losses, 'b-', label='Training Loss')
    plt.plot(epochs, val_losses, 'r-', label='Validation Loss')
    plt.title('Loss Curves')
    plt.xlabel('Epoch')
    plt.ylabel('Loss Value')
    plt.legend()
    plt.grid(True)
    
    # 绘制Dice系数
    plt.subplot(2, 2, 2)
    plt.plot(epochs, train_dices, 'b-', label='Training Dice')
    plt.plot(epochs, val_dices, 'r-', label='Validation Dice')
    plt.title('Dice Coefficient Curves')
    plt.xlabel('Epoch')
    plt.ylabel('Dice Coefficient')
    plt.legend()
    plt.grid(True)
    
    # 绘制损失（对数尺度）
    plt.subplot(2, 2, 3)
    plt.semilogy(epochs, train_losses, 'b-', label='Training Loss')
    plt.semilogy(epochs, val_losses, 'r-', label='Validation Loss')
    plt.title('Loss Curves (Log Scale)')
    plt.xlabel('Epoch')
    plt.ylabel('Log Loss Value')
    plt.legend()
    plt.grid(True)
    
    # 绘制最近N个epoch的损失
    n_recent = min(10, len(train_losses))  # 最近10个epoch或全部（如果少于10个）
    plt.subplot(2, 2, 4)
    if len(train_losses) > n_recent:
        recent_epochs = range(len(train_losses) - n_recent + 1, len(train_losses) + 1)
        plt.plot(recent_epochs, train_losses[-n_recent:], 'b-', label='Training Loss')
        plt.plot(recent_epochs, val_losses[-n_recent:], 'r-', label='Validation Loss')
    else:
        plt.plot(epochs, train_losses, 'b-', label='Training Loss')
        plt.plot(epochs, val_losses, 'r-', label='Validation Loss')
    plt.title(f'Recent {n_recent} Epochs Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss Value')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, f'training_curves_epoch_{len(train_losses)}.png'))
    # 保存一个带时间戳的副本
    plt.savefig(os.path.join(save_dir, 'training_history.png'))
    plt.close()
    
    # 创建单独的高分辨率损失曲线图像
    plt.figure(figsize=(15, 8))
    plt.plot(epochs, train_losses, 'bo-', linewidth=2, markersize=8, label='Training Loss')
    plt.plot(epochs, val_losses, 'ro-', linewidth=2, markersize=8, label='Validation Loss')
    plt.title('Loss Curves', fontsize=16)
    plt.xlabel('Epoch', fontsize=14)
    plt.ylabel('Loss', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True)
    plt.xticks(epochs[::max(1, len(epochs)//10)])  # 显示合理数量的x轴刻度
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, f'loss_curve_epoch_{len(train_losses)}.png'))
    plt.close()
    
    # 创建单独的高分辨率Dice曲线图像
    plt.figure(figsize=(15, 8))
    plt.plot(epochs, train_dices, 'bo-', linewidth=2, markersize=8, label='Training Dice')
    plt.plot(epochs, val_dices, 'ro-', linewidth=2, markersize=8, label='Validation Dice')
    plt.title('Dice Coefficient Curves', fontsize=16)
    plt.xlabel('Epoch', fontsize=14)
    plt.ylabel('Dice Coefficient', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True)
    plt.xticks(epochs[::max(1, len(epochs)//10)])  # 显示合理数量的x轴刻度
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, f'dice_curve_epoch_{len(train_losses)}.png'))
    plt.close()


def visualize_predictions(model, x_test, y_test, device, num_samples=5, save_dir=None):
    """
    可视化模型预测结果
    """
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        
    # 随机选择样本
    indices = random.sample(range(len(x_test)), min(num_samples, len(x_test)))
    
    plt.figure(figsize=(15, 5 * num_samples))
    
    model.eval()
    with torch.no_grad():
        for i, idx in enumerate(indices):
            # 获取图像和标签
            image = x_test[idx]
            true_mask = y_test[idx]
            
            # 准备输入
            image_tensor = torch.from_numpy(image).float().unsqueeze(0).unsqueeze(0).to(device)
            
            # 预测掩码
            pred_mask = model(image_tensor).squeeze().cpu().numpy()
            
            # 二值化预测掩码
            pred_mask_binary = (pred_mask > 0.5).astype(np.float32)
            
            # 计算Dice系数
            dice = dice_coeff(torch.from_numpy(pred_mask_binary).unsqueeze(0).unsqueeze(0),
                             torch.from_numpy(true_mask).unsqueeze(0).unsqueeze(0)).item()
            
            # 可视化
            plt.subplot(num_samples, 3, i * 3 + 1)
            plt.imshow(image, cmap='gray')
            plt.title('原始图像')
            plt.axis('off')
            
            plt.subplot(num_samples, 3, i * 3 + 2)
            plt.imshow(true_mask, cmap='gray')
            plt.title('真实掩码')
            plt.axis('off')
            
            plt.subplot(num_samples, 3, i * 3 + 3)
            plt.imshow(pred_mask, cmap='gray')
            plt.title(f'预测掩码 (Dice: {dice:.4f})')
            plt.axis('off')
    
    plt.tight_layout()
    
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'predictions.png'))
        plt.close()
    else:
        plt.show()


def main():
    # 从环境变量获取设置
    data_dir = os.environ.get('DATA_DIR', 'data/processed/unet_training_data')
    output_dir = os.environ.get('OUTPUT_DIR', 'models/unet')
    num_epochs = int(os.environ.get('NUM_EPOCHS', 50))
    batch_size = int(os.environ.get('BATCH_SIZE', 4))
    learning_rate = float(os.environ.get('LEARNING_RATE', 1e-4))
    img_size_w = int(os.environ.get('IMG_SIZE_W', 512))
    img_size_h = int(os.environ.get('IMG_SIZE_H', 512))
    grad_accumulation_steps = int(os.environ.get('GRAD_ACCUMULATION_STEPS', 1))
    checkpoint_interval = int(os.environ.get('CHECKPOINT_INTERVAL', 5))
    patience = int(os.environ.get('PATIENCE', 10))
    validation_split = float(os.environ.get('VALIDATION_SPLIT', 0.2))


    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 准备数据路径
    train_file_path = os.path.join(data_dir, 'train_files.txt')
    val_file_path = os.path.join(data_dir, 'val_files.txt')

    if not (os.path.exists(train_file_path) and os.path.exists(val_file_path)):
        print(f"错误: {train_file_path} 或 {val_file_path} 不存在。")
        print("请先运行 '0_prepare_unet_data.py' 来生成这些文件。")
        return
        
    x_train_paths, y_train_paths = get_data_paths(data_dir, train_file_path)
    x_val_paths, y_val_paths = get_data_paths(data_dir, val_file_path)

    
    # 创建数据集
    img_size = (img_size_w, img_size_h)
    train_dataset = FileBasedNoduleDataset(x_train_paths, y_train_paths, img_size=img_size)
    val_dataset = FileBasedNoduleDataset(x_val_paths, y_val_paths, img_size=img_size)
    
    # 创建数据加载器
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)
    
    # 初始化模型、损失函数和优化器
    model = UNet(n_channels=1, n_classes=1).to(device)
    criterion = DiceBCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # 打印模型摘要
    print(model)
    
    # 训练模型
    print("开始训练...")
    
    # 修改train_model函数以支持梯度累积和混合精度训练
    def train_model_with_grad_accumulation(model, train_loader, val_loader, criterion, optimizer, device,
                                         num_epochs, output_dir, grad_accumulation_steps=1, 
                                         patience=10, checkpoint_interval=5):
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        checkpoint_dir = os.path.join(output_dir, 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # 创建梯度缩放器用于混合精度训练
        
        # 创建日志文件
        log_file = os.path.join(output_dir, 'training_log.csv')
        with open(log_file, 'w') as f:
            f.write('epoch,train_loss,train_dice,val_loss,val_dice\n')
        
        # 用于记录训练过程
        train_losses = []
        val_losses = []
        train_dices = []
        val_dices = []
        
        # 用于早停
        best_val_loss = float('inf')
        patience_counter = 0
        best_model_path = os.path.join(output_dir, 'model-best.pth')
        
        # 检查是否存在检查点
        start_epoch = 0
        latest_checkpoint = None
        
        # 查找最新的检查点
        if os.path.exists(checkpoint_dir):
            checkpoints = sorted([f for f in os.listdir(checkpoint_dir) if f.startswith('checkpoint_epoch_')])
            if checkpoints:
                latest_checkpoint = checkpoints[-1]
                start_epoch = int(latest_checkpoint.split('_')[-1].split('.')[0])
                
                # 加载检查点
                checkpoint_path = os.path.join(checkpoint_dir, latest_checkpoint)
                print(f"加载检查点: {checkpoint_path}")
                checkpoint = torch.load(checkpoint_path, map_location=device)
                model.load_state_dict(checkpoint['model_state_dict'])
                optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
                train_losses = checkpoint['train_losses']
                val_losses = checkpoint['val_losses']
                train_dices = checkpoint['train_dices']
                val_dices = checkpoint['val_dices']
                best_val_loss = checkpoint['best_val_loss']
                patience_counter = checkpoint['patience_counter']
                
    
                    
                print(f"从 epoch {start_epoch} 恢复训练")
        
        # 训练循环
        for epoch in range(start_epoch, num_epochs):
            # 训练阶段
            model.train()
            train_loss = 0
            train_dice = 0
            optimizer.zero_grad()  # 确保开始时梯度为零
            
            for i, (images, masks) in enumerate(tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Train]")):
                # 清除缓存以减少内存使用
                if device.type == 'cuda':
                    torch.cuda.empty_cache()
                    
                # 将数据移到设备
                images = images.to(device)
                masks = masks.to(device)
                
              
                # 前向传播 (使用全精度)
                outputs = model(images)
                loss = criterion(outputs, masks) / grad_accumulation_steps  # 根据累积步数缩小损失
                
                # 计算Dice系数
                train_dice += dice_coeff(outputs, masks).item()
                
                # 反向传播但不立即优化
                loss.backward()
                
                # 累积梯度若干步后更新参数
                if (i + 1) % grad_accumulation_steps == 0 or (i + 1) == len(train_loader):
                    # 梯度裁剪，防止梯度爆炸
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    
                    optimizer.step()
                    optimizer.zero_grad()
                
                train_loss += loss.item() * grad_accumulation_steps  # 恢复原始损失值
                
                # 主动释放GPU内存
                del images, masks, outputs, loss
                if device.type == 'cuda':
                    torch.cuda.empty_cache()
            
            # 计算平均损失和Dice系数
            train_loss /= len(train_loader)
            train_dice /= len(train_loader)
            train_losses.append(train_loss)
            train_dices.append(train_dice)
            
            # 验证阶段
            model.eval()
            val_loss = 0
            val_dice = 0
            
            with torch.no_grad():
                for images, masks in tqdm(val_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Valid]"):
                    # 清除缓存以减少内存使用
                    if device.type == 'cuda':
                        torch.cuda.empty_cache()
                        
                    # 将数据移到设备
                    images = images.to(device)
                    masks = masks.to(device)
                    
                    # 使用混合精度进行预测
                   
                    # 前向传播
                    outputs = model(images)
                    loss = criterion(outputs, masks)
                    # 计算Dice系数
                    val_dice += dice_coeff(outputs, masks).item()
                    
                    val_loss += loss.item()
                    
                    # 主动释放GPU内存
                    del images, masks, outputs, loss
                    if device.type == 'cuda':
                        torch.cuda.empty_cache()
            
            # 计算平均损失和Dice系数
            val_loss /= len(val_loader)
            val_dice /= len(val_loader)
            val_losses.append(val_loss)
            val_dices.append(val_dice)
            
            # 写入日志文件
            with open(log_file, 'a') as f:
                f.write(f'{epoch+1},{train_loss:.6f},{train_dice:.6f},{val_loss:.6f},{val_dice:.6f}\n')
            
            # 打印训练信息
            print(f"Epoch {epoch+1}/{num_epochs}, "
                  f"Train Loss: {train_loss:.4f}, Train Dice: {train_dice:.4f}, "
                  f"Val Loss: {val_loss:.4f}, Val Dice: {val_dice:.4f}")
            
            # 实时绘制和保存训练曲线
            plot_training_results(train_losses, val_losses, train_dices, val_dices, output_dir)
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                torch.save(model.state_dict(), best_model_path)
                print(f"Best model saved with val_loss: {best_val_loss:.4f}")
                
                # 保存最佳模型的指标
                with open(os.path.join(output_dir, 'best_model_metrics.json'), 'w') as f:
                    import json
                    json.dump({
                        'epoch': epoch + 1,
                        'train_loss': train_loss,
                        'train_dice': train_dice,
                        'val_loss': val_loss,
                        'val_dice': val_dice
                    }, f, indent=4)
            else:
                patience_counter += 1
                if patience_counter >= 3:
                    print(f"早停! 在 {epoch+1} 轮后没有改善")
                    break
            
            # 定期保存检查点
            if (epoch + 1) % checkpoint_interval == 0 or (epoch + 1) == num_epochs:
                checkpoint_path = os.path.join(checkpoint_dir, f'checkpoint_epoch_{epoch+1}.pth')
                checkpoint_data = {
                    'epoch': epoch + 1,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'train_losses': train_losses,
                    'val_losses': val_losses,
                    'train_dices': train_dices,
                    'val_dices': val_dices,
                    'best_val_loss': best_val_loss,
                    'patience_counter': patience_counter
                }
               
                    
                torch.save(checkpoint_data, checkpoint_path)
                print(f"检查点已保存: {checkpoint_path}")
        
        # 保存最终模型
        torch.save(model.state_dict(), os.path.join(output_dir, 'model-final.pth'))
        
        # 保存完整训练历史
        history = {
            'train_loss': train_losses,
            'val_loss': val_losses,
            'train_dice': train_dices,
            'val_dice': val_dices
        }
        
        # 保存到JSON文件
        with open(os.path.join(output_dir, 'training_history.json'), 'w') as f:
            import json
            json.dump(history, f, indent=4)
        
        # 绘制训练结果
        plot_training_results(train_losses, val_losses, train_dices, val_dices, output_dir)
        
        return train_losses, val_losses, train_dices, val_dices
    
    # 使用带梯度累积的训练函数
    train_losses, val_losses, train_dices, val_dices = train_model_with_grad_accumulation(
        model, train_loader, val_loader, criterion, optimizer, device, num_epochs, 
        output_dir, grad_accumulation_steps=grad_accumulation_steps, 
        checkpoint_interval=checkpoint_interval
    )
    
    # 加载最佳模型
    model.load_state_dict(torch.load(os.path.join(output_dir, 'model-best.pth')))
    
    # 可视化预测结果
    print("可视化预测结果...")
    visualize_predictions(model, x_val_paths, y_val_paths, device, num_samples=5, save_dir=output_dir)
    
    print(f"训练完成! 模型已保存到: {output_dir}")


if __name__ == "__main__":
    main() 