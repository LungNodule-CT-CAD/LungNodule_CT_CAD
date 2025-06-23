import random
from io import BytesIO

import pydicom
from pydicom.errors import InvalidDicomError
from predict import run_prediction, get_model

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

@app.on_event("startup")
async def startup_event():
    """在应用启动时预加载模型。"""
    get_model()

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
    接收上传的单个CT图像文件，使用 PyTorch 模型进行真实的肺结节检测。
    """
    # 1. 读取上传的文件内容
    contents = await file.read()

    # 2. 调用模型进行预测
    # predict.py 中的 run_prediction 函数负责处理所有逻辑
    nodule_dicts = run_prediction(contents)

    # 3. 将返回的字典列表转换为 Pydantic 模型列表
    # FastAPI 会使用它来验证响应数据
    nodules = [Nodule(**n) for n in nodule_dicts]
        
    return {"nodules": nodules} 