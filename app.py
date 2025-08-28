import io
import os
import base64
from typing import Optional
from dataclasses import dataclass

from flask import Flask, request, jsonify, send_file
from PIL import Image
import numpy as np

# =============== Config & Globals ===============
BACKEND = os.getenv("BACKEND", "lama").lower() # lama | sd15
LAMA_ENDPOINT = os.getenv("LAMA_ENDPOINT", "").strip() # e.g. http://lama-cleaner:8080
SD15_MODEL = os.getenv("SD15_MODEL", "runwayml/stable-diffusion-inpainting")
SD_STEPS = int(os.getenv("SD_STEPS", "35"))
SD_GUIDANCE = float(os.getenv("SD_GUIDANCE", "7.0"))
SD_MAX_SIDE = int(os.getenv("SD_MAX_SIDE", "896"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024 # 25MB

_sd_pipe = None # lazy loaded

# =============== Utils ===============

def b64_to_pil(data_uri: str) -> Image.Image:
  """Convert data URI (data:image/png;base64,...) to PIL.Image."""
  if not isinstance(data_uri, str) or "base64," not in data_uri:
  raise ValueError("Invalid data URI")
  b64 = data_uri.split("base64,", 1)[1]
  raw = base64.b64decode(b64)
  img = Image.open(io.BytesIO(raw))
  return img.convert("RGBA")

def pil_to_b64(pil: Image.Image, fmt: str = "PNG") -> str:
  buf = io.BytesIO()
  pil.save(buf, format=fmt)
  buf.seek(0)
  return "data:image/png;base64," + base64.b64encode(buf.read()).decode("utf-8")

def rgba_to_rgb(pil: Image.Image, bg=(255, 255, 255)) -> Image.Image:
  if pil.mode == "RGB":
    return pil
  bg_img = Image.new("RGB", pil.size, bg)
  bg_img.paste(pil, mask=pil.split()[-1] if pil.mode == "RGBA" else None)
  return bg_img

# =============== Inpainting Backends ===============

def get_sd_pipe():
  global _sd_pipe
  if _sd_pipe is not None:
    return _sd_pipe
  from diffusers import StableDiffusionInpaintPipeline
  import torch

  device = "cuda" if torch.cuda.is_available() else "cpu"
  pipe = StableDiffusionInpaintPipeline.from_pretrained(
    SD15_MODEL,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    safety_checker=None,
  )
if device == "cuda":
  pipe = pipe.to("cuda")
else:
  try:
    pipe.enable_sequential_cpu_offload()
  except Exception:
    pass
  _sd_pipe = pipe
  return _sd_pipe

def inpaint_sd15(img_rgba: Image.Image, mask_rgba: Image.Image, prompt: str = "") -> Image.Image:
  pipe = get_sd_pipe()

  img = img_rgba.convert("RGB")
  mask = mask_rgba.convert("L")

  # Resize for quality/speed tradeoff
  w, h = img.size
  scale = min(SD_MAX_SIDE / max(w, h), 1.0)
  new_size = (
    max(64, int(w * scale)) // 8 * 8,
    max(64, int(h * scale)) // 8 * 8,
  )
  img_r = img.resize(new_size, Image.LANCZOS)
  mask_r = mask.resize(new_size, Image.NEAREST)

  out = pipe(
    prompt=(prompt or "seamless, natural background reconstruction, detailed textures"),
    image=img_r,
    mask_image=mask_r,
    guidance_scale=SD_GUIDANCE,
    num_inference_steps=SD_STEPS,
    strength=0.99,
  ).images[0]

  if new_size != (w, h):
    out = out.resize((w, h), Image.LANCZOS)
  return out

def inpaint_lama_http(img_rgba: Image.Image, mask_rgba: Image.Image, prompt: str = "") -> Image.Image:
  """Call lama-cleaner HTTP server. See: https://github.com/Sanster/lama-cleaner
  Expected endpoint: POST {LAMA_ENDPOINT}/inpaint with multipart form fields:
  - image: file (PNG/JPEG)
  - mask: file (PNG, white = inpaint area)
  - prompt (optional)
"""
  import requests

  if not LAMA_ENDPOINT:
    raise RuntimeError("LAMA_ENDPOINT is not configured")

  img_io = io.BytesIO()
  mask_io = io.BytesIO()
  rgba_to_rgb(img_rgba).save(img_io, format="PNG")
  mask_rgba.convert("L").save(mask_io, format="PNG")
  img_io.seek(0); mask_io.seek(0)

  files = {
    "image": ("image.png", img_io, "image/png"),
    "mask": ("mask.png", mask_io, "image/png"),
  }
  data = {"prompt": prompt}

  url = LAMA_ENDPOINT.rstrip("/") + "/inpaint"
  resp = requests.post(url, files=files, data=data, timeout=120)
  if resp.status_code != 200:
    raise RuntimeError(f"LaMA HTTP failed: {resp.status_code} {resp.text[:200]}")

  # Assume server returns PNG bytes
  out = Image.open(io.BytesIO(resp.content)).convert("RGB")
  return out

# =============== Routes ===============

@app.get("/")
def home():
  return (
    "<h3>AI Watermark Remover API</h3>"
    "<ul>"
    "<li>POST /api/remove — JSON: image (dataURI), mask (dataURI), prompt</li>"
    "<li>POST /api/auto_mask — JSON: image (dataURI), returns mask (dataURI) — Florence‑2 (预留)</li>"
    f"<li>Backend: {BACKEND} | LAMA_ENDPOINT: {'set' if LAMA_ENDPOINT else 'not set'}</li>"
    "</ul>"
  )

@app.post("/api/remove")
def api_remove():
  """Main inpaint endpoint: returns dataURI PNG."""
  try:
    data = request.get_json(force=True)
    img_uri = data.get("image")
    mask_uri = data.get("mask")
    prompt = data.get("prompt", "")

    if not img_uri or not mask_uri:
      return jsonify({"ok": False, "error": "image and mask are required"}), 400

    img_pil = b64_to_pil(img_uri)
    mask_pil = b64_to_pil(mask_uri)

    # Normalize mask to binary white(=inpaint)
    mask_gray = mask_pil.convert("L")
    mask_bin = Image.fromarray((np.array(mask_gray) > 10).astype(np.uint8) * 255)

    if BACKEND == "lama":
      if not LAMA_ENDPOINT:
        # Fall back to sd15 if LAMA endpoint missing
        out_pil = inpaint_sd15(img_pil, mask_bin, prompt)
      else:
        out_pil = inpaint_lama_http(img_pil, mask_bin, prompt)
  else:
    out_pil = inpaint_sd15(img_pil, mask_bin, prompt)

  return jsonify({"ok": True, "image": pil_to_b64(out_pil, fmt="PNG")})
except Exception as e:
  return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/auto_mask")
def api_auto_mask():
  """(预留) Florence‑2 自动检测水印，返回 mask 的 dataURI。
  你可以在下一步引入 Florence‑2 推理代码，或把该逻辑放到独立服务。
  现在暂时返回 501，便于先联调 inpaint 主流程。
  """
  return jsonify({
    "ok": False,
    "error": "Florence‑2 auto-mask not implemented in this step. Provide a user-drawn mask for now.",
  }), 501

@app.post("/api/ping")
def api_ping():
  return jsonify({
  "ok": True,
  "backend": BACKEND,
  "lama_endpoint": bool(LAMA_ENDPOINT),
  })

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=8000, debug=True)
