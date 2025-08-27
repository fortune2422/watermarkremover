from flask import Flask, request, render_template, send_file
import cv2
import numpy as np
import pytesseract
import os
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

# 手动模式
@app.route("/remove", methods=["POST"])
def remove():
    file = request.files["image"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    x, y, w, h = int(request.form["x"]), int(request.form["y"]), int(request.form["w"]), int(request.form["h"])
    img = cv2.imread(filepath)

    mask = np.zeros(img.shape[:2], np.uint8)
    mask[y:y+h, x:x+w] = 255

    dst = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)
    outpath = os.path.join(RESULT_FOLDER, "manual_" + filename)
    cv2.imwrite(outpath, dst)

    return send_file(outpath, mimetype="image/png")

# 自动识别模式
@app.route("/auto_remove", methods=["POST"])
def auto_remove():
    file = request.files["image"]
    img = Image.open(file.stream).convert("RGB")
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # OCR 识别水印文字
    data = pytesseract.image_to_data(img_cv, output_type=pytesseract.Output.DICT)

    mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)

    for i, text in enumerate(data["text"]):
        if "jili707.net" in text.lower():  # 只针对水印
            (x, y, w, h) = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
            mask[y:y+h, x:x+w] = 255  # 标记要去掉的区域

    # 修复图像
    result = cv2.inpaint(img_cv, mask, 3, cv2.INPAINT_TELEA)

    _, buffer = cv2.imencode(".png", result)
    return Response(buffer.tobytes(), mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
