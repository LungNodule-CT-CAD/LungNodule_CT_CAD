import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, WeightedRandomSampler
from torchvision import datasets, transforms
from pathlib import Path
import argparse
import logging
import copy
import numpy as np
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt

from cnn_classifier_model import get_classifier_model

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../output/logs/train_cnn.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def plot_and_save_curves(history, save_path):
    """绘制并保存训练和验证的损失和准确率曲线"""
    try:
        plt.figure(figsize=(18, 6))

        # 绘制损失曲线
        plt.subplot(1, 2, 1)
        plt.plot(history['train_loss'], label='Train Loss')
        plt.plot(history['val_loss'], label='Validation Loss')
        plt.title('Loss Curves')
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True)

        # 绘制准确率曲线
        plt.subplot(1, 2, 2)
        plt.plot(history['train_acc'], label='Train Accuracy')
        plt.plot(history['val_acc'], label='Validation Accuracy')
        plt.title('Accuracy Curves')
        plt.xlabel('Epochs')
        plt.ylabel('Accuracy')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        
        # 确保目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path)
        logger.info(f"训练曲线图已保存至: {save_path}")
        plt.close()
    except Exception as e:
        logger.error(f"无法保存曲线图: {e}")

def train_model(model, dataloaders, criterion, optimizer, device, class_names, num_epochs=25):
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}

    for epoch in range(num_epochs):
        logger.info(f'Epoch {epoch+1}/{num_epochs}')
        logger.info('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0
            all_labels = []
            all_preds = []

            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                all_labels.extend(labels.cpu().numpy())
                all_preds.extend(preds.cpu().numpy())
            
            epoch_loss = running_loss / len(dataloaders[phase].dataset)
            epoch_acc = running_corrects.double() / len(dataloaders[phase].dataset)
            
            if phase == 'train':
                history['train_loss'].append(epoch_loss)
                history['train_acc'].append(epoch_acc.item())
            else:
                history['val_loss'].append(epoch_loss)
                history['val_acc'].append(epoch_acc.item())
            
            logger.info(f'{phase.capitalize()} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            # 打印分类报告
            report = classification_report(all_labels, all_preds, target_names=class_names, zero_division=0)
            logger.info(f'\nClassification Report for {phase}:\n{report}')

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
                logger.info(f'New best validation accuracy: {best_acc:.4f}!')

    logger.info(f'Best val Acc: {best_acc:4f}')
    model.load_state_dict(best_model_wts)
    return model, history

def main():
    parser = argparse.ArgumentParser(description="训练CNN分类器以区分真假肺结节")
    parser.add_argument("--data-dir", type=str, default="../data/processed/cnn_classifier_dataset", help="包含fp和tp子目录的数据集路径")
    parser.add_argument("--output-model-path", type=str, default="../models/cnn_classifier.pth", help="保存最佳模型的路径")
    parser.add_argument("--output-curves-path", type=str, default="../output/logs/training_curves.png", help="保存训练曲线图的路径")
    parser.add_argument("--batch-size", type=int, default=32, help="训练批次大小")
    parser.add_argument("--epochs", type=int, default=20, help="训练轮次")
    parser.add_argument("--lr", type=float, default=0.0001, help="学习率")
    parser.add_argument("--val-split", type=float, default=0.2, help="验证集所占比例")
    parser.add_argument("--arch", type=str, default="efficientnet_b0", choices=["efficientnet_b0", "resnet101", "resnet100"], help="用于分类的骨干网络架构")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")

    # --- 数据预处理和加载 ---
    # ResNet需要3通道输入，并使用ImageNet的均值和标准差进行归一化
    data_transforms = {
        'train': transforms.Compose([
            transforms.Grayscale(num_output_channels=3), # 将灰度图转换为3通道
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) # ImageNet 归一化
        ]),
        'val': transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"数据目录不存在: {data_dir}")
        return

    full_dataset = datasets.ImageFolder(data_dir)
    
    # 划分训练集和验证集
    num_data = len(full_dataset)
    num_val = int(num_data * args.val_split)
    num_train = num_data - num_val
    train_dataset, val_dataset = random_split(full_dataset, [num_train, num_val])

    # 为训练集和验证集应用不同的变换
    train_dataset.dataset.transform = data_transforms['train']
    val_dataset.dataset.transform = data_transforms['val']
    
    # --- 计算类别权重以实现加权采样 ---
    logger.info("为处理数据不平衡问题，配置加权采样器...")
    class_counts = np.bincount(full_dataset.targets)
    logger.info(f"原始样本数量 (fp, tp): {class_counts}")
    
    # 为每个样本计算权重
    class_weights_sampler = 1. / class_counts
    sample_weights = np.array([class_weights_sampler[t] for t in full_dataset.targets])
    
    # 只在训练集上使用加权采样
    train_indices = train_dataset.indices
    train_sample_weights = torch.from_numpy(sample_weights[train_indices]).double()
    
    sampler = WeightedRandomSampler(train_sample_weights, len(train_sample_weights))

    dataloaders = {
        'train': DataLoader(train_dataset, batch_size=args.batch_size, sampler=sampler, num_workers=2),
        'val': DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2)
    }
    
    class_names = full_dataset.classes
    logger.info(f"数据集类别: {full_dataset.class_to_idx}")
    logger.info(f"训练集大小: {len(train_dataset)}, 验证集大小: {len(val_dataset)}")

    # --- 计算用于损失函数的类别权重 ---
    class_counts_tensor = torch.tensor(class_counts, dtype=torch.float)
    class_weights_loss = class_counts_tensor.sum() / class_counts_tensor
    class_weights_loss = class_weights_loss.to(device)
    logger.info(f"计算出的损失函数权重: {class_weights_loss}")

    # --- 模型、损失函数、优化器 ---
    model = get_classifier_model(arch=args.arch).to(device)
    # 使用加权的损失函数
    criterion = nn.CrossEntropyLoss(weight=class_weights_loss)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    # --- 开始训练 ---
    best_model, history = train_model(model, dataloaders, criterion, optimizer, device, class_names, num_epochs=args.epochs)
    
    # --- 保存最佳模型 ---
    torch.save(best_model.state_dict(), args.output_model_path)
    logger.info(f"训练完成. 最佳模型已保存至: {args.output_model_path}")

    # --- 保存可视化曲线 ---
    plot_and_save_curves(history, args.output_curves_path)

if __name__ == '__main__':
    main() 