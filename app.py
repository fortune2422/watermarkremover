import cv2
import numpy as np
import os
from flask import Flask, request, render_template, send_file
from io import BytesIO
from PIL import Image

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/remove", methods=["POST"])
def remove():
    file = request.files["image"]
    x = int(request.form.get("x"))
    y = int(request.form.get("y"))
    w = int(request.form.get("w"))
    h = int(request.form.get("h"))
    
    # 处理负数宽高（保证左上角起点）
    if w < 0:
        x += w
        w = -w
    if h < 0:
        y += h
        h = -h

    img = np.array(Image.open(file).convert("RGB"))
    mask = np.zeros(img.shape[:2], np.uint8)

    # 设置水印区域
    mask[y:y+h, x:x+w] = 255

    # inpaint 修复
    dst = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)

    # 返回图片
    output = Image.fromarray(dst)
    buf = BytesIO()
    output.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
