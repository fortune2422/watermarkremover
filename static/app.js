const fileInput = document.getElementById("fileInput");
const imageCanvas = document.getElementById("imageCanvas");
const maskCanvas = document.getElementById("maskCanvas");
const ctxImg = imageCanvas.getContext("2d");
const ctxMask = maskCanvas.getContext("2d");
const resultImg = document.getElementById("resultImg");


let drawing = false;
let image = new Image();


fileInput.addEventListener("change", e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    image.onload = () => {
      imageCanvas.width = image.width;
      imageCanvas.height = image.height;
      maskCanvas.width = image.width;
      maskCanvas.height = image.height;
      ctxImg.drawImage(image, 0, 0);
      ctxMask.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    };
    image.src = reader.result;
  };
  reader.readAsDataURL(file);
});

maskCanvas.addEventListener("mousedown", () => drawing = true);
maskCanvas.addEventListener("mouseup", () => drawing = false);
maskCanvas.addEventListener("mouseout", () => drawing = false);
maskCanvas.addEventListener("mousemove", e => {
  if (!drawing) return;
  const rect = maskCanvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  ctxMask.fillStyle = "rgba(255,255,255,1)";
  ctxMask.beginPath();
  ctxMask.arc(x, y, 10, 0, Math.PI * 2);
  ctxMask.fill();
});

document.getElementById("clearBtn").onclick = () => {
  ctxMask.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
};

document.getElementById("uploadBtn").onclick = async () => {
  if (!fileInput.files[0]) return alert("请先上传图片");
  maskCanvas.toBlob(async maskBlob => {
    const formData = new FormData();
    formData.append("image", fileInput.files[0]);
    formData.append("mask", maskBlob, "mask.png");

    const res = await fetch("/upload", { method: "POST", body: formData });
    if (res.ok) {
      const blob = await res.blob();
      resultImg.src = URL.createObjectURL(blob);
    } else {
    alert("去水印失败");
    }
  });
};
