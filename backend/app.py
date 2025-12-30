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
origins = [
    "http://localhost:3000",
    "https://seimu-app.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 保存用ディレクトリ
UPLOAD_DIR = "uploaded_receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. 静的ファイル（画面・画像）の提供設定
# ---------------------------------------------------------
# frontendフォルダを /static でアクセス可能に
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 保存された画像を /uploads でアクセス可能にする（★追加機能）
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ルート（/）にアクセスしたら index.html を表示する
@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# ---------------------------------------------------------
# 2. APIエンドポイント
# ---------------------------------------------------------

# 画像アップロード
@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "success",
        "filename": filename,
        "message": "クラウドへの保存に成功しました！",
        "path": file_path
    }

# 保存された画像の一覧を取得（★追加機能）
@app.get("/api/ocr/list")
async def list_receipts():
    if not os.path.exists(UPLOAD_DIR):
        return {"files": []}
    
    # ファイル名を取得して、新しい順（降順）に並び替え
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    # .DS_Storeなどの不要なファイルを除外
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    
    return {"files": image_files}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)