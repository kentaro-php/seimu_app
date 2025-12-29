from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from datetime import datetime

app = FastAPI()

# ---------------------------------------------------------
# CORS設定 (フロントエンドからの接続を許可)
# ---------------------------------------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 保存用フォルダを自動作成
UPLOAD_DIR = "uploaded_receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# ルート確認用
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "message": "政務活動費自動分別API (シンプル版)",
        "version": "1.0.0",
        "endpoints": ["/api/ocr/upload"]
    }

# ----------------------------------
@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    # 1. ファイル名を決定 (現在時刻をつける)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 2. ファイルを保存する
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. 成功メッセージを返す
    return {
        "status": "success",
        "filename": filename,
        "message": "画像をサーバーに保存しました！",
        "path": file_path
    }

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from datetime import datetime
import uvicorn

app = FastAPI()

# ---------------------------------------------------------
# CORS設定
# ---------------------------------------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 保存用フォルダ作成
UPLOAD_DIR = "uploaded_receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# ルート確認用
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {
        "message": "政務活動費自動分別API (シンプル版)",
        "version": "1.0.0",
        "endpoints": ["/api/ocr/upload"]
    }

# ---------------------------------------------------------------------
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
        "message": "画像をサーバーに保存しました！",
        "path": file_path
    }

# ---------------------------------------------------------
# 起動スイッチ (これが重要！)
# ---------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

