import io
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
