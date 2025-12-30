def analyze_receipt_with_ai(file_path):
    api_key = os.getenv("GOOGLE_API_KEY")
    # APIキーがない場合のハンドリング
    if not api_key:
        print("⚠️ APIキーが Render の Environment Variables に設定されていません")
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": 0,
            "store": "APIキー設定エラー",
            "category": "未分類",
            "note": "Renderの設定画面で GOOGLE_API_KEY を追加してください"
        }

    try:
        genai.configure(api_key=api_key)
        
        img = Image.open(file_path)

        prompt = """
        このレシート画像を解析し、以下のJSONスキーマに従って情報を抽出してください。
        日付が不明な場合は本日の日付を入れてください。
        費目は「調査研究費, 研修費, 会議費, 資料作成費, 資料購入費, 広報費, 広聴費, 人件費, 事務所費, その他」の中から最も適切なものを選んでください。
        """

        # ★Gemini 2.0 Flash-Lite を指定
        # モデル名は "gemini-2.0-flash-lite-preview-02-05" を使用します
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite-preview-02-05",
            generation_config={"response_mime_type": "application/json"}
        )
        
        print("🤖 Gemini 2.0 Flash-Lite で解析中...")
        response = model.generate_content([prompt, img])
        
        # テキストをJSONとしてロード
        return json.loads(response.text)

    except Exception as e:
        print(f"❌ AI解析エラー: {e}")
        # 詳細なエラーログを出力
        import traceback
        traceback.print_exc()
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "amount": 0,
            "store": "解析失敗",
            "category": "未分類",
            "note": "手動で入力してください"
        }
