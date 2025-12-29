"""
政務活動費自動分別アプリ - FastAPIバックエンド
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import json
import io
import base64
from collections import defaultdict

# モックデータベース（本番環境ではFirestoreを使用）
receipts_db = {}
receipt_counter = 0

app = FastAPI(
    title="政務活動費自動分別API",
    description="領収書のOCR認識と費目自動分類を行うAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データモデル
class Receipt(BaseModel):
    receipt_id: Optional[str] = None
    user_id: str = "default_user"
    date: str
    store: str
    category: str
    total: float
    note: Optional[str] = ""
    image_url: Optional[str] = ""
    apportionment: Optional[float] = 100.0  # 按分率（%）

class CategoryUpdate(BaseModel):
    receipt_id: str
    category: str
    note: Optional[str] = ""

class SummaryQuery(BaseModel):
    user_id: str = "default_user"
    year: int
    month: Optional[int] = None

# 費目分類ロジック
CATEGORIES = {
    "調査研究費": ["調査", "研究", "視察", "交通費", "宿泊", "ホテル", "航空券", "新幹線", "タクシー"],
    "研修費": ["研修", "セミナー", "講習", "勉強会", "参加費", "受講"],
    "広報費": ["印刷", "広報", "チラシ", "ポスター", "看板", "新聞広告", "Web制作"],
    "広聴費": ["アンケート", "座談会", "意見交換", "ヒアリング", "調査票"],
    "要請・陳情活動費": ["陳情", "要請", "交渉", "協議", "面会"],
    "会議費": ["会議", "会合", "懇親会", "茶菓子", "弁当", "飲料", "レストラン"],
    "資料作成費": ["コピー", "製本", "編集", "デザイン", "文具", "インク"],
    "資料購入費": ["書籍", "雑誌", "新聞", "資料", "図書", "購読"],
    "人件費": ["給与", "賃金", "報酬", "謝金", "アルバイト", "派遣"],
    "事務所費": ["家賃", "光熱費", "通信費", "電話", "インターネット", "電気", "ガス", "水道"]
}

def classify_category(text: str) -> str:
    """
    テキストから費目を自動分類
    """
    text_lower = text.lower()
    
    # 各費目のキーワードマッチング
    scores = defaultdict(int)
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                scores[category] += 1
    
    # 最もスコアが高い費目を返す
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    return "未分類"

def mock_ocr(image_data: bytes) -> dict:
    """
    モックOCR処理（本番環境ではGoogle Cloud Vision APIを使用）
    """
    return {
        "store": "サンプル書店",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total": 3500,
        "items": ["書籍 政治学入門", "領収書"]
    }

# APIエンドポイント

@app.get("/")
def read_root():
    return {
        "message": "政務活動費自動分別API",
        "version": "1.0.0",
        "endpoints": [
            "/api/ocr/upload",
            "/api/classify",
            "/api/receipt/save",
            "/api/receipt/list",
            "/api/summary",
            "/api/export/pdf",
            "/api/export/csv"
        ]
    }

@app.post("/api/ocr/upload")
async def upload_receipt(file: UploadFile = File(...)):
    """
    領収書画像をアップロードしてOCR処理
    """
    try:
        # 画像データを読み込み
        contents = await file.read()
        
        # モックOCR処理
        ocr_result = mock_ocr(contents)
        
        # テキストから費目を自動分類
        text = f"{ocr_result['store']} {' '.join(ocr_result['items'])}"
        category = classify_category(text)
        
        # 画像をBase64エンコード
        image_base64 = base64.b64encode(contents).decode()
        
        return {
            "success": True,
            "data": {
                "store": ocr_result["store"],
                "date": ocr_result["date"],
                "total": ocr_result["total"],
                "category": category,
                "image_url": f"data:image/jpeg;base64,{image_base64[:100]}..."  # 省略版
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/classify")
def classify_text(text: str):
    """
    テキストから費目を分類
    """
    category = classify_category(text)
    return {
        "text": text,
        "category": category,
        "confidence": 0.85
    }

@app.post("/api/receipt/save")
def save_receipt(receipt: Receipt):
    """
    領収書データを保存
    """
    global receipt_counter
    
    if not receipt.receipt_id:
        receipt_counter += 1
        receipt.receipt_id = f"R{receipt_counter:06d}"
    
    receipts_db[receipt.receipt_id] = receipt.dict()
    
    return {
        "success": True,
        "receipt_id": receipt.receipt_id,
        "message": "領収書を保存しました"
    }

@app.get("/api/receipt/list")
def list_receipts(user_id: str = "default_user", year: Optional[int] = None, month: Optional[int] = None):
    """
    領収書一覧を取得
    """
    receipts = [r for r in receipts_db.values() if r["user_id"] == user_id]
    
    # 年月でフィルタ
    if year:
        receipts = [r for r in receipts if r["date"].startswith(str(year))]
    if month:
        month_str = f"-{month:02d}-"
        receipts = [r for r in receipts if month_str in r["date"]]
    
    # 日付でソート
    receipts.sort(key=lambda x: x["date"], reverse=True)
    
    return {
        "success": True,
        "count": len(receipts),
        "receipts": receipts
    }

@app.post("/api/receipt/update")
def update_category(update: CategoryUpdate):
    """
    費目を手動で修正
    """
    if update.receipt_id not in receipts_db:
        raise HTTPException(status_code=404, detail="領収書が見つかりません")
    
    receipts_db[update.receipt_id]["category"] = update.category
    if update.note:
        receipts_db[update.receipt_id]["note"] = update.note
    
    return {
        "success": True,
        "message": "費目を更新しました"
    }

@app.post("/api/summary")
def get_summary(query: SummaryQuery):
    """
    月別・費目別の集計を取得
    """
    receipts = [r for r in receipts_db.values() if r["user_id"] == query.user_id]
    
    # 年月でフィルタ
    if query.year:
        receipts = [r for r in receipts if r["date"].startswith(str(query.year))]
    if query.month:
        month_str = f"-{query.month:02d}-"
        receipts = [r for r in receipts if month_str in r["date"]]
    
    # 費目別集計
    category_summary = defaultdict(float)
    for receipt in receipts:
        amount = receipt["total"] * (receipt.get("apportionment", 100.0) / 100.0)
        category_summary[receipt["category"]] += amount
    
    total = sum(category_summary.values())
    
    return {
        "success": True,
        "period": f"{query.year}年" + (f"{query.month}月" if query.month else ""),
        "total": total,
        "by_category": dict(category_summary),
        "receipt_count": len(receipts)
    }

@app.get("/api/export/csv")
def export_csv(user_id: str = "default_user", year: Optional[int] = None, month: Optional[int] = None):
    """
    CSV形式でエクスポート
    """
    receipts = [r for r in receipts_db.values() if r["user_id"] == user_id]
    
    if year:
        receipts = [r for r in receipts if r["date"].startswith(str(year))]
    if month:
        month_str = f"-{month:02d}-"
        receipts = [r for r in receipts if month_str in r["date"]]
    
    # CSV生成
    csv_content = "領収書ID,日付,店舗名,費目,金額,按分率,備考\n"
    for receipt in receipts:
        csv_content += f"{receipt['receipt_id']},{receipt['date']},{receipt['store']},"
        csv_content += f"{receipt['category']},{receipt['total']},{receipt.get('apportionment', 100.0)},"
        csv_content += f"\"{receipt.get('note', '')}\"\n"
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=receipts_{year}_{month}.csv"}
    )

@app.get("/api/export/pdf")
def export_pdf(user_id: str = "default_user", year: Optional[int] = None, month: Optional[int] = None):
    """
    PDF形式でエクスポート（議会提出用）
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 日本語フォント設定
        try:
            pdfmetrics.registerFont(TTFont('Japanese', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'))
            font_name = 'Japanese'
        except:
            font_name = 'Helvetica'
        
        receipts = [r for r in receipts_db.values() if r["user_id"] == user_id]
        
        if year:
            receipts = [r for r in receipts if r["date"].startswith(str(year))]
        if month:
            month_str = f"-{month:02d}-"
            receipts = [r for r in receipts if month_str in r["date"]]
        
        # PDF生成
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # タイトル
        p.setFont(font_name, 16)
        p.drawString(30*mm, height - 30*mm, f"政務活動費報告書 {year}年{month}月" if month else f"{year}年")
        
        # 集計
        category_summary = defaultdict(float)
        for receipt in receipts:
            amount = receipt["total"] * (receipt.get("apportionment", 100.0) / 100.0)
            category_summary[receipt["category"]] += amount
        
        y_pos = height - 50*mm
        p.setFont(font_name, 12)
        
        for category, amount in category_summary.items():
            p.drawString(30*mm, y_pos, f"{category}: ¥{amount:,.0f}")
            y_pos -= 7*mm
        
        total = sum(category_summary.values())
        p.setFont(font_name, 14)
        p.drawString(30*mm, y_pos - 10*mm, f"合計: ¥{total:,.0f}")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_{year}_{month}.pdf"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="PDFライブラリがインストールされていません")

@app.get("/api/categories")
def get_categories():
    """
    利用可能な費目一覧を取得
    """
    return {
        "categories": list(CATEGORIES.keys()),
        "count": len(CATEGORIES)
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("政務活動費自動分別アプリ - サーバー起動中...")
    print("=" * 60)
    print("📱 APIドキュメント: http://localhost:8000/docs")
    print("🌐 フロントエンド: http://localhost:3000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
