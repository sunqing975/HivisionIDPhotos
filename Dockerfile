FROM python:3.10-slim-bookworm

# 系统依赖：OpenCV/FFmpeg 运行所需（锁 Debian 12；libgl1 替代 trixie 中已移除的 libgl1-mesa-glx）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-app.txt ./

RUN pip install --no-cache-dir -r requirements.txt -r requirements-app.txt

COPY . .

# 下载 MODNet 抠图模型（官方 GitHub Releases，24.7MB；模型不存入 git 仓库，构建时拉取）
RUN mkdir -p hivision/creator/weights && \
    curl -fL --retry 5 --retry-delay 3 -o hivision/creator/weights/modnet_photographic_portrait_matting.onnx \
    https://github.com/Zeyi-Lin/HivisionIDPhotos/releases/download/pretrained-model/modnet_photographic_portrait_matting.onnx

EXPOSE 80

# 证件照 API（uvicorn，独立启动器支持端口参数），云托管默认监听 80
CMD ["python3", "-u", "run_api_8081.py", "80"]
