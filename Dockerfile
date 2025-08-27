# 使用官方 Python 镜像
FROM python:3.10-slim

# 设置时区和防止交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖，包括 tesseract-ocr 和 opencv 相关库
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动 Flask
CMD ["python", "app.py"]
