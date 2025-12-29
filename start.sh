#!/bin/bash
echo "政務活動費アプリを起動中..."

# バックエンドをバックグラウンドで起動 (& をつける)
python backend/app.py &

# 3秒待機 (サーバーの立ち上がり待ち)
sleep 3

# フロントエンドをバックグラウンドで起動
python -m http.server 3000 --directory frontend &

echo ""
echo "アプリが起動しました！"
echo "ブラウザで http://localhost:3000 を開いてください"
echo "終了するには Ctrl+C を押してください（その後、バックグラウンドのプロセスも終了する必要があります）"

# プロセスが終了しないように待機
wait
