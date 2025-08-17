import torch.nn as nn
from torchvision import models

def get_classifier_model(arch: str = 'efficientnet_b0', num_classes: int = 2, pretrained: bool = True):
    """根据 *arch* 返回对应的预训练模型，并将最后分类层替换为 ``num_classes`` 输出。

    支持:
    1. efficientnet_b0  (默认)
    2. resnet101  (用户提出的"resnet100"将自动映射为 resnet101)
    """

    arch = arch.lower()

    if arch in {'efficientnet', 'efficientnet_b0', 'effb0'}:
        # EfficientNet-B0
        model = models.efficientnet_b0(pretrained=pretrained)
        num_ftrs = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(num_ftrs, num_classes)

    elif arch in {'resnet100', 'resnet101'}:
        # torchvision 没有 resnet100，使用最接近的 resnet101
        model = models.resnet101(pretrained=pretrained)
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, num_classes)

    else:
        raise ValueError(f"暂不支持的架构: {arch}. 请选择 'efficientnet_b0' 或 'resnet101'.")

    return model

# --- 以下是旧的自定义模型，保留作为参考 ---
# class NoduleClassifier(nn.Module):
#     def __init__(self):
#         super(NoduleClassifier, self).__init__()
#         self.features = nn.Sequential(
#             nn.Conv2d(1, 16, kernel_size=3, padding=1),
#             nn.ReLU(inplace=True),
#             nn.MaxPool2d(kernel_size=2, stride=2),
            
#             nn.Conv2d(16, 32, kernel_size=3, padding=1),
#             nn.ReLU(inplace=True),
#             nn.MaxPool2d(kernel_size=2, stride=2),
            
#             nn.Conv2d(32, 64, kernel_size=3, padding=1),
#             nn.ReLU(inplace=True),
#             nn.MaxPool2d(kernel_size=2, stride=2),
            
#             nn.Conv2d(64, 128, kernel_size=3, padding=1),
#             nn.ReLU(inplace=True),
#             nn.MaxPool2d(kernel_size=2, stride=2),
#         )
#         self.classifier = nn.Sequential(
#             nn.Dropout(),
#             nn.Linear(128 * 4 * 4, 256),
#             nn.ReLU(inplace=True),
#             nn.Dropout(),
#             nn.Linear(256, 2),
#         )

#     def forward(self, x):
#         x = self.features(x)
#         x = x.view(x.size(0), -1)
#         x = self.classifier(x)
#         return x 