const imageCanvas = document.getElementById("imageCanvas");
const maskCanvas = document.getElementById("maskCanvas");
const ctx = imageCanvas.getContext("2d");
const maskCtx = maskCanvas.getContext("2d");
const uploadInput = document.getElementById("uploadInput");
const uploadButton = document.getElementById("uploadButton");

let drawing = false;

// 上传图片并绘制在 canvas 上
uploadInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    const img = new Image();
    img.onload = () => {
      imageCanvas.width = img.width;
      imageCanvas.height = img.height;
      maskCanvas.width = img.width;
      maskCanvas.height = img.height;

      ctx.drawImage(img, 0, 0, img.width, img.height);
      maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    };
    img.src = event.target.result;
  };
  reader.readAsDataURL(file);
});

// 遮罩绘制（黑色区域 = 需要去掉）
maskCanvas.addEventListener("mousedown", () => { drawing = true; });
maskCanvas.addEventListener("mouseup", () => { drawing = false; maskCtx.beginPath(); });
maskCanvas.addEventListener("mousemove", drawMask);

function drawMask(e) {
  if (!drawing) return;
  const rect = maskCanvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  maskCtx.lineWidth = 30;
  maskCtx.lineCap = "round";
  maskCtx.strokeStyle = "white"; // 白色表示需要去掉
  maskCtx.lineTo(x, y);
  maskCtx.stroke();
  maskCtx.beginPath();
  maskCtx.moveTo(x, y);
}

// 点击按钮 → 发送 JSON 给后端
uploadButton.addEventListener("click", async () => {
  const imageData = imageCanvas.toDataURL("image/png");
  const maskData = maskCanvas.toDataURL("image/png");

  const res = await fetch("/api/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageData, mask: maskData })
  });

  if (res.ok) {
    const data = await res.json();
    const resultImg = new Image();
    resultImg.src = data.result; // 后端返回的 data:image/png;base64
    document.body.appendChild(resultImg);
  } else {
    alert("去水印失败");
  }
});
