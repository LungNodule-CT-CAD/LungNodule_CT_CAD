"""
Backend server using FastAPI to serve the lung nodule detection model.
"""
import logging
import uvicorn
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from predict import run_prediction, get_models

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- FastAPI 应用初始化 ---
app = FastAPI(
    title="Lung Nodule Detection API",
    description="Uses a U-Net model to detect lung nodules from CT images by segmentation.",
    version="1.0.0",
)

# --- CORS 跨域设置 ---
# 允许指定的来源进行跨域请求。
origins = [
    "http://localhost",
    "http://localhost:3000",    # React,    # Vite 默认开发端口
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "https://spectacular-daifuku-30b99d.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 应用启动事件 ---
@app.on_event("startup")
async def startup_event():
    """在应用启动时预加载模型。"""
    logger.info("正在预加载模型...")
    try:
        get_models()  # 调用模型加载函数
        logger.info("模型预加载成功！")
    except Exception as e:
        logger.error(f"模型预加载失败: {e}", exc_info=True)
        # 在启动失败时，最好让应用挂掉，以便容器或进程管理器可以重启它
        raise e


# --- API 数据模型 (Pydantic) ---
class Point(BaseModel):
    x: int
    y: int

class Nodule(BaseModel):
    id: int
    contour: List[Point]

class NoduleDetectResponse(BaseModel):
    nodules: List[Nodule]


# --- API 端点 ---
@app.get("/")
def read_root():
    """根路径，用于快速测试服务器是否正在运行。"""
    return {"status": "healthy", "message": "Lung Nodule Detection API is running."}


@app.post("/api/predict", response_model=NoduleDetectResponse)
async def predict_endpoint(file: UploadFile = File(...)):
    """
    接收上传的单个CT图像文件，进行单阶段肺结节检测，并返回结节的轮廓点集。
    """
    logger.info(f"接收到文件进行预测: {file.filename}")
    try:
        # 1. 读取上传的文件内容
        image_bytes = await file.read()
        
        # 2. 调用模型进行预测
        results = run_prediction(image_bytes)
        
        logger.info(f"成功处理图像 {file.filename}，检测到 {len(results)} 个结节。")
        # 3. 按照 Pydantic 模型结构返回结果
        return {"nodules": results}

    except Exception as e:
        logger.error(f"处理文件 {file.filename} 时发生错误: {e}", exc_info=True)
        # 向客户端抛出 HTTP 500 错误
        raise HTTPException(status_code=500, detail=f"An error occurred during prediction: {str(e)}")


# --- 直接运行时的启动配置 ---
if __name__ == '__main__':
    # 此配置使得 `python main.py` 也能启动 uvicorn 服务器
    uvicorn.run(app, host="0.0.0.0", port=8000) 