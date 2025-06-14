import random
from io import BytesIO

import pydicom
from pydicom.errors import InvalidDicomError

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

# 1. FastAPI 应用初始化
app = FastAPI(
    title="CT Lung Nodule Detection - Mock API",
    description="A mock API server for the frontend of the CT Lung Nodule Detection System.",
    version="1.0.0",
)

# 2. CORS 跨域设置
# 允许所有来源的请求，这对于本地开发非常方便。
# 在生产环境中，应将其限制为前端应用的实际域名。
origins = [
    "http://localhost",
    "http://localhost:3000",  # 默认的 Vite React 前端地址
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 请求头
)

# 3. 数据模型定义 (使用 Pydantic)
class Nodule(BaseModel):
    id: int
    x: int
    y: int
    width: int
    height: int

class NoduleDetectResponse(BaseModel):
    nodules: list[Nodule]

# --- API Endpoints ---

@app.get("/")
def read_root():
    """根路径，用于快速测试服务器是否正在运行。"""
    return {"message": "CT Nodule Detection Mock API is running."}


@app.post("/api/detect-nodules", response_model=NoduleDetectResponse)
async def detect_nodules(file: UploadFile = File(...)):
    """
    接收上传的单个CT图像文件，模拟肺结节检测。
    它会尝试读取图像尺寸以生成合理的随机坐标，然后返回一个包含2到5个随机生成的结节信息的列表。
    """
    contents = await file.read()
    image_stream = BytesIO(contents)

    # 设置默认图像尺寸
    image_width, image_height = 512, 512

    try:
        # 尝试作为 DICOM 文件读取
        # force=True 有助于处理一些不完全符合标准的文件
        dcm = pydicom.dcmread(image_stream, force=True)
        # DICOM 像素数组的 shape 通常是 (行, 列) -> (高, 宽)
        if hasattr(dcm, 'pixel_array') and len(dcm.pixel_array.shape) >= 2:
            image_height, image_width = dcm.pixel_array.shape[:2]
    except InvalidDicomError:
        # 如果不是有效的 DICOM 文件，则尝试作为常规图像文件（PNG, JPG等）打开
        try:
            # 重置 BytesIO 的指针，因为 pydicom.dcmread 可能已经移动了它
            image_stream.seek(0)
            image = Image.open(image_stream)
            image_width, image_height = image.size
        except Exception:
            # 如果两种方式都失败，则使用默认的 512x512 尺寸
            pass

    nodules = []
    # 随机生成 2 到 5 个结节
    num_nodules = random.randint(2, 5)
    
    for i in range(num_nodules):
        # 为防止无限循环，设置单个结节位置生成的尝试次数上限
        for _ in range(50): # 最多尝试50次
            # 随机生成结节的尺寸 (10到40像素)
            nodule_w = random.randint(10, 40)
            nodule_h = random.randint(10, 40)
            
            # 随机生成结节的位置，确保不会超出图像边界
            if image_width > nodule_w and image_height > nodule_h:
                nodule_x = random.randint(0, image_width - nodule_w)
                nodule_y = random.randint(0, image_height - nodule_h)
            else: # 如果图像太小，无法生成结节
                nodule_x, nodule_y = 0, 0

            # --- 防重叠检测 ---
            is_overlapping = False
            for existing_nodule in nodules:
                # 检查两个矩形是否重叠
                if (nodule_x < existing_nodule.x + existing_nodule.width and
                    nodule_x + nodule_w > existing_nodule.x and
                    nodule_y < existing_nodule.y + existing_nodule.height and
                    nodule_y + nodule_h > existing_nodule.y):
                    is_overlapping = True
                    break # 发生重叠，跳出内部循环，重新生成
            
            if not is_overlapping:
                nodules.append(
                    Nodule(
                        id=len(nodules) + 1,
                        x=nodule_x,
                        y=nodule_y,
                        width=nodule_w,
                        height=nodule_h,
                    )
                )
                break # 成功找到不重叠的位置，跳出尝试循环，继续生成下一个结节
        
    return {"nodules": nodules} 