from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
import json
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
CRITERIA_DIR = "criteria_files"  # 按分基準ファイル用
DATA_FILE = "data.json"          # 収入などの設定保存用

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CRITERIA_DIR, exist_ok=True)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# データ読み書き用関数
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"income": 0}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ---------------------------------------------------------
# APIエンドポイント
# ---------------------------------------------------------

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# 1. 収入・残高などのステータス取得
@app.get("/api/status")
async def get_status():
    data = load_data()
    income = data.get("income", 0)
    
    # ※現在はOCR未実装のため、支出はダミー計算（ファイル数×1000円など）または固定値
    # 本来はデータベースから集計します
    file_count = len([f for f in os.listdir(UPLOAD_DIR) if f != '.gitkeep'])
    expenses = file_count * 5000 # 仮：レシート1枚5000円として計算
    
    balance = income - expenses
    
    # 基準ファイル名の取得
    criteria_files = os.listdir(CRITERIA_DIR)
    criteria_name = criteria_files[0] if criteria_files else "未設定"

    return {
        "income": income,
        "expenses": expenses,
        "balance": balance,
        "criteria_file": criteria_name
    }

# 2. 収入（予算）の設定
@app.post("/api/settings/income")
async def set_income(income: int = Form(...)):
    data = load_data()
    data["income"] = income
    save_data(data)
    return {"status": "success", "income": income}

# 3. 按分基準ファイルのアップロード
@app.post("/api/settings/criteria")
async def upload_criteria(file: UploadFile = File(...)):
    # 古いファイルを削除（1つだけ保持するため）
    for f in os.listdir(CRITERIA_DIR):
        os.remove(os.path.join(CRITERIA_DIR, f))
    
    file_path = os.path.join(CRITERIA_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "success", "filename": file.filename}

# 4. レシート画像のアップロード
@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": "success", "filename": filename, "message": "Saved"}

# 5. 画像リスト取得
@app.get("/api/ocr/list")
async def list_receipts():
    if not os.path.exists(UPLOAD_DIR):
        return {"files": []}
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf'))]
    return {"files": image_files}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
