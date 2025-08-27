import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file
from io import BytesIO
from PIL import Image

app = Flask(__name__)

@app.route("/remove_watermark", methods=["POST"])
def remove_watermark():
    file = request.files["image"]
    x = int(request.form.get("x"))
    y = int(request.form.get("y"))
    w = int(request.form.get("w"))
    h = int(request.form.get("h"))

    # 读取图片
    img = np.array(Image.open(file).convert("RGB"))
    mask = np.zeros(img.shape[:2], np.uint8)

    # 设置水印区域
    mask[y:y+h, x:x+w] = 255

    # inpaint 修复
    dst = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)

    # 返回结果
    output = Image.fromarray(dst)
    buf = BytesIO()
    output.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/")
def home():
    return "✅ 上传图片到 /remove_watermark 接口"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
