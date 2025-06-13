import base64
import random
from io import BytesIO

import numpy as np
import pydicom
from pydicom.pixel_data_handlers.util import apply_voi_lut

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
class WindowAdjustRequest(BaseModel):
    ww: int
    wl: int
    image: str

class NoduleDetectRequest(BaseModel):
    image: str

class Nodule(BaseModel):
    id: int
    x: int
    y: int
    width: int
    height: int

class NoduleDetectResponse(BaseModel):
    nodules: list[Nodule]

class ImageResponse(BaseModel):
    image: str

# --- API Endpoints ---

@app.get("/")
def read_root():
    """根路径，用于快速测试服务器是否正在运行。"""
    return {"message": "CT Nodule Detection Mock API is running."}


@app.post("/api/upload", response_model=ImageResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    接收上传的DCM或标准图像文件，将其转换为PNG格式，并以Base64字符串形式返回。
    这模拟了图像上传和初步处理的流程，增加了对DICOM格式的支持。
    """
    contents = await file.read()
    
    try:
        # 尝试作为 DICOM 文件读取
        dicom_file = pydicom.dcmread(BytesIO(contents))
        
        # 应用 VOI LUT (Value of Interest Look-Up Table) 来获取最佳可视化效果
        # 这是正确显示医学图像的关键步骤
        array = apply_voi_lut(dicom_file.pixel_array, dicom_file)
        
        # 将像素数据归一化到 8-bit (0-255)
        if array.dtype != np.uint8:
            array = array.astype(float)
            array = (np.maximum(array, 0) / array.max()) * 255.0
            array = array.astype(np.uint8)

        image = Image.fromarray(array)

    except pydicom.errors.InvalidDicomError:
        # 如果不是有效的 DICOM 文件，则尝试作为常规图像文件（PNG, JPG等）打开
        try:
            image = Image.open(BytesIO(contents))
        except Exception:
            # 如果两种方式都失败，则会触发一个500错误，这在开发中是可接受的
            raise

    # 转换为PNG格式，以便在Web上获得最佳兼容性
    output_buffer = BytesIO()
    image.save(output_buffer, format="PNG")
    png_data = output_buffer.getvalue()
    
    # 将PNG数据编码为Base64字符串
    base64_string = base64.b64encode(png_data).decode("utf-8")
    
    return {"image": f"data:image/png;base64,{base64_string}"}


@app.post("/api/adjust-window", response_model=ImageResponse)
async def adjust_window(request: WindowAdjustRequest):
    """
    接收包含WW/WL值的Base64编码图像，应用窗宽窗位调整，并返回处理后的新图像。
    这个实现为前端提供了一个真实的、即时可见的图像处理效果。
    """
    # 1. 从请求中获取数据
    base64_image_data = request.image
    ww = request.ww
    wl = request.wl

    # 2. 解码Base64图像
    # Base64字符串通常带有 'data:image/png;base64,' 前缀，需要移除
    header, encoded = base64_image_data.split(",", 1)
    image_data = base64.b64decode(encoded)
    
    # 将解码后的数据读入Pillow Image对象
    image = Image.open(BytesIO(image_data))
    
    # 3. 应用窗宽窗位调整
    # 将图像转换为NumPy数组以便进行数学运算
    # 我们假设图像是8位灰度图，因为web通常如此
    img_array = np.array(image.convert("L"), dtype=float)

    # 计算窗宽的上下限
    window_low = wl - ww / 2
    window_high = wl + ww / 2

    # 应用窗口调整
    # - 将窗口内的数据线性拉伸到0-255
    # - 窗口外的数据置为0或255
    img_array = (img_array - window_low) / (window_high - window_low) * 255.0
    
    # 将超出范围的值裁剪到0-255
    img_array[img_array < 0] = 0
    img_array[img_array > 255] = 255
    
    # 转换回8位无符号整数
    adjusted_array = img_array.astype(np.uint8)

    # 4. 将处理后的数组转换回Pillow图像
    adjusted_image = Image.fromarray(adjusted_array)

    # 5. 将新图像编码为Base64字符串
    output_buffer = BytesIO()
    adjusted_image.save(output_buffer, format="PNG")
    png_data = output_buffer.getvalue()
    
    base64_string = base64.b64encode(png_data).decode("utf-8")

    return {"image": f"data:image/png;base64,{base64_string}"}


@app.post("/api/detect-nodules", response_model=NoduleDetectResponse)
async def detect_nodules(request: NoduleDetectRequest):
    """
    模拟肺结节检测。
    忽略输入的图像，并返回一个包含3个随机生成的结节坐标的列表。
    """
    nodules = []
    # 假设图像尺寸为 512x512，我们在此范围内生成结节
    image_width, image_height = 512, 512
    
    for i in range(3):
        # 随机生成结节的尺寸 (10到40像素)
        nodule_w = random.randint(10, 40)
        nodule_h = random.randint(10, 40)
        
        # 随机生成结节的位置，确保不会超出图像边界
        nodule_x = random.randint(0, image_width - nodule_w)
        nodule_y = random.randint(0, image_height - nodule_h)
        
        nodules.append(
            Nodule(
                id=i + 1,
                x=nodule_x,
                y=nodule_y,
                width=nodule_w,
                height=nodule_h,
            )
        )
        
    return {"nodules": nodules} 