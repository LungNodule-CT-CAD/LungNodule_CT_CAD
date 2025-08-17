# U-Net 两阶段检测 src 目录简明指南

本目录包含肺结节两阶段检测与微调的核心代码，覆盖 **数据准备 ➜ 模型训练 / 微调 ➜ 推断评估 ➜ FN 再利用** 全链路。

## 文件结构

```text
src/
├─ unet_model.py              # U-Net 网络结构
├─ 3_train_unet.py            # 训练 U-Net（分割）
├─ 2_prepare_cnn.py           # U-Net 预测 → 提取 tp/fp patch
├─ 4_train_cnn_classifier.py  # 训练 CNN（二分类）
├─ 5_evaluate_two_stage.py    # U-Net + CNN 两阶段评估
├─ extract_fn_dataset.py      # 导出 FN 切片生成微调数据集
├─ finetune_unet.py           # 在 FN 数据上微调 U-Net
└─ cnn_classifier_model.py    # ResNet / EfficientNet 等分类器封装
```

## 常用流程

> 所有命令均在 `src/` 目录执行，路径请按实际情况调整。

### 0. 准备数据集

1. **放置原始 LIDC DICOM**
   ```text
   ../data/raw/
     LIDC-IDRI-0001/  ← 原始 DICOM 目录层级保持不变
     LIDC-IDRI-0002/
     ...
   ```

2. **解析 XML -> PNG 掩码、灰度图**
   ```bash
   python 0_prepare_unet_data.py \
     --dicom-dir   ../data/raw \
     --save-dir    ../data/processed/ground_truth_dataset
   ```
   该脚本会：
   - 读取 `*.dcm` 与对应 XML 标注
   - 生成对齐的 512×512 `images/` 与 `masks/`
   - 输出 `train_files.txt / val_files.txt / test_files.txt`

3. **过滤无结节切片**
   ```bash
   python filter_dataset.py --data-dir ../data/processed/ground_truth_dataset
   ```
   只保留含结节或负样本的必要切片，减少训练 IO。

### 1. 训练 U-Net

```bash
python 3_train_unet.py \
  --epochs 60 \
  --lr 1e-4
# 👉 最优模型默认保存至 ../models/unet/model-best.pth
```

### 2. 生成 CNN 训练数据并训练分类器

```bash
# 2.1 由 U-Net 预测结果生成 tp / fp patch
python 2_prepare_cnn.py \
  --model-path ../models/unet/model-best.pth \
  --dicom-dir  ../data/raw

# 2.2 训练 CNN
python 4_train_cnn_classifier.py \
  --data-dir ../data/processed/cnn_classifier_dataset \
  --arch efficientnet_b0 \
  --epochs 20
```

### 3. 两阶段评估

```bash
python 5_evaluate_two_stage.py \
  --unet-model ../models/unet/model-best.pth \
  --cnn-model  ../models/cnn_classifier.pth \
  --dicom-dir  ../data/raw \
  --output-dir ../output/predictions/evaluation
```

### 4. 导出 FN 切片并微调 U-Net

```bash
# 4.1 提取 FN 数据集
python extract_fn_dataset.py \
  --unet-model ../models/unet/model-best.pth \
  --cnn-model  ../models/cnn_classifier.pth \
  --dicom-dir  ../data/raw \
  --ground-truth-json ../data/processed/ground_truth_dataset/ground_truth_inventory.json \
  --save-dir fn_dataset

# 4.2 在 FN 数据上微调 U-Net
python finetune_unet.py \
  --fn-data-dir fn_dataset \
  --pretrained-model ../models/unet/model-best.pth \
  --output-path ../models/unet/model-finetuned.pth \
  --epochs 15 --lr 5e-5 --freeze-encoder
```

### 5. 使用微调后模型再次评估

```bash
python 5_evaluate_two_stage.py \
  --unet-model ../models/unet/model-finetuned.pth \
  --cnn-model  ../models/cnn_classifier.pth \
  --dicom-dir  ../data/raw
```

## 脚本亮点

1. **类别不平衡双保险**：同时使用 `WeightedRandomSampler` 与加权 CE。  
2. **可插拔分类器**：`--arch` 选择 EfficientNet-B0 / ResNet101 等。  
3. **三通道仿真 + ImageNet 归一化**：无需改首层即可用预训练模型。  
4. **训练过程可视化**：自动保存 Loss / Accuracy 曲线 PNG。  
5. **FN 微调闭环**：`extract_fn_dataset.py` + `finetune_unet.py` 快速提升召回率。

> 代码包含充分注释，可按需进一步定制。 