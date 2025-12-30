from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
import json
from datetime import datetime
import uvicorn
from pydantic import BaseModel
from PIL import Image
import google.generativeai as genai

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
CRITERIA_DIR = "criteria_files"
DATA_FILE = "data.json"
RECEIPTS_DB = "receipts.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CRITERIA_DIR, exist_ok=True)

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

class ReceiptData(BaseModel):
    date: str = ""
    amount: int = 0
    store: str = ""
    category: str = "未分類"
    note: str = ""

# --- AI処理関数 (Google Gemini 1.5 Flash) ---
def analyze_receipt_with_ai(file_path):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️ APIキーがないためダミーOCRを実行します")
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": 0,
            "store": "APIキー未設定",
            "category": "未分類",
            "note": "Renderの環境変数に GOOGLE_API_KEY を設定してください"
        }

    try:
        genai.configure(api_key=api_key)
        # 高速・安価な Flash モデルを使用
        model = genai.GenerativeModel('gemini-1.5-flash')

        # 画像を開く
        img = Image.open(file_path)

        prompt = """
        あなたは政務活動費の経理担当AIです。
        このレシート画像を解析し、以下の情報をJSON形式で抽出してください。
        
        出力フォーマット(JSONのみ出力):
        {
          "date": "YYYY-MM-DD",
          "amount": 数字のみ(円),
          "store": "店名",
          "category": "費目",
          "note": "内容の要約"
        }

        費目の選択肢:
        調査研究費, 研修費, 広聴広報費, 要請陳情等活動費, 会議費, 資料作成費, 資料購入費, 人件費, 事務所費
        
        ※日付が読み取れない場合は今日の日付を入れてください。
        ※JSON以外の余計な文字（```json 等）は含めないでください。
        """

        response = model.generate_content([prompt, img])
        
        # 結果の整形
        result_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(result_text)

    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": 0,
            "store": "読取エラー",
            "category": "未分類",
            "note": str(e)
        }

# --- API ---

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

@app.get("/api/status")
async def get_status():
    settings = load_json(DATA_FILE, {"income": 0})
    receipts = load_json(RECEIPTS_DB, {})
    total_expenses = sum(r.get("amount", 0) for r in receipts.values())
    balance = settings.get("income", 0) - total_expenses
    c_files = os.listdir(CRITERIA_DIR)
    
    return {
        "income": settings.get("income", 0),
        "expenses": total_expenses,
        "balance": balance,
        "criteria_file": c_files[0] if c_files else "未設定"
    }

@app.post("/api/settings/income")
async def set_income(income: int = Form(...)):
    data = load_json(DATA_FILE, {})
    data["income"] = income
    save_json(DATA_FILE, data)
    return {"status": "success"}

@app.post("/api/settings/criteria")
async def upload_criteria(file: UploadFile = File(...)):
    for f in os.listdir(CRITERIA_DIR):
        os.remove(os.path.join(CRITERIA_DIR, f))
    file_path = os.path.join(CRITERIA_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success"}

@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # AIで解析（Gemini）
    ai_data = analyze_receipt_with_ai(file_path)

    # DBに保存
    db = load_json(RECEIPTS_DB, {})
    db[filename] = {
        "filename": filename,
        "date": ai_data.get("date", ""),
        "amount": ai_data.get("amount", 0),
        "category": ai_data.get("category", "未分類"),
        "store": ai_data.get("store", ""),
        "note": ai_data.get("note", "")
    }
    save_json(RECEIPTS_DB, db)

    return {"status": "success", "filename": filename, "data": db[filename]}

@app.post("/api/receipts/{filename}")
async def update_receipt(filename: str, data: ReceiptData):
    db = load_json(RECEIPTS_DB, {})
    if filename in db:
        db[filename].update(data.dict())
        save_json(RECEIPTS_DB, db)
        return {"status": "success", "data": db[filename]}
    return {"status": "error", "message": "File not found"}

@app.get("/api/ocr/list")
async def list_receipts():
    db = load_json(RECEIPTS_DB, {})
    valid_list = []
    if os.path.exists(UPLOAD_DIR):
        files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
        for f in files:
            if f in db:
                valid_list.append(db[f])
            elif f.lower().endswith(('.png', '.jpg', '.jpeg')):
                valid_list.append({"filename": f, "amount": 0, "category": "未分類"})
    return {"files": valid_list}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
