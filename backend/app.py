from fastapi import FastAPI, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
import json
from datetime import datetime
import uvicorn
from typing import Optional
from pydantic import BaseModel

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ディレクトリ・ファイル設定
UPLOAD_DIR = "uploaded_receipts"
CRITERIA_DIR = "criteria_files"
DATA_FILE = "data.json"           # 全体設定（収入など）
RECEIPTS_DB = "receipts.json"     # レシート個別のデータ（金額、費目など）

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CRITERIA_DIR, exist_ok=True)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- データ管理用関数 ---
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- データモデル ---
class ReceiptData(BaseModel):
    date: str = ""
    amount: int = 0
    store: str = ""
    category: str = "未分類"
    note: str = ""

# --- API ---

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# 1. 全体ステータス取得（リアルな支出計算）
@app.get("/api/status")
async def get_status():
    # 設定データの読み込み
    settings = load_json(DATA_FILE, {"income": 0})
    income = settings.get("income", 0)
    
    # レシートデータの読み込み・集計
    receipts = load_json(RECEIPTS_DB, {})
    total_expenses = sum(r.get("amount", 0) for r in receipts.values())
    
    balance = income - total_expenses
    
    # 基準ファイル名
    c_files = os.listdir(CRITERIA_DIR)
    c_name = c_files[0] if c_files else "未設定"

    return {
        "income": income,
        "expenses": total_expenses,
        "balance": balance,
        "criteria_file": c_name
    }

# 2. 収入設定
@app.post("/api/settings/income")
async def set_income(income: int = Form(...)):
    data = load_json(DATA_FILE, {})
    data["income"] = income
    save_json(DATA_FILE, data)
    return {"status": "success"}

# 3. 基準ファイルアップロード
@app.post("/api/settings/criteria")
async def upload_criteria(file: UploadFile = File(...)):
    for f in os.listdir(CRITERIA_DIR):
        os.remove(os.path.join(CRITERIA_DIR, f))
    file_path = os.path.join(CRITERIA_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success"}

# 4. 画像アップロード（初期データ作成）
@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # DBに空データを登録
    db = load_json(RECEIPTS_DB, {})
    db[filename] = {
        "filename": filename,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "amount": 0,
        "category": "未分類",
        "store": "",
        "note": ""
    }
    save_json(RECEIPTS_DB, db)

    return {"status": "success", "filename": filename}

# 5. レシート詳細データの保存（編集機能）
@app.post("/api/receipts/{filename}")
async def update_receipt(filename: str, data: ReceiptData):
    db = load_json(RECEIPTS_DB, {})
    if filename in db:
        db[filename].update(data.dict())
        save_json(RECEIPTS_DB, db)
        return {"status": "success", "data": db[filename]}
    return {"status": "error", "message": "File not found"}

# 6. レシート一覧取得（データ付き）
@app.get("/api/ocr/list")
async def list_receipts():
    db = load_json(RECEIPTS_DB, {})
    # ファイルが存在するものだけを返す
    valid_list = []
    if os.path.exists(UPLOAD_DIR):
        files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
        for f in files:
            if f in db:
                valid_list.append(db[f])
            elif f.lower().endswith(('.png', '.jpg', '.jpeg')):
                # DBにないけどファイルがある場合（手動追加など）
                valid_list.append({"filename": f, "amount": 0, "category": "未分類"})
    
    return {"files": valid_list}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
