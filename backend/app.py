from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
from datetime import datetime
import uvicorn

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ディレクトリ設定
UPLOAD_DIR = "uploaded_receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# 画像アップロードAPI
@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": "success", "filename": filename, "message": "Saved"}

# 画像リスト取得API
@app.get("/api/ocr/list")
async def list_receipts():
    if not os.path.exists(UPLOAD_DIR):
        return {"files": []}
    
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    return {"files": image_files}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
