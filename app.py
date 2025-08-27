import cv2
import numpy as np
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
