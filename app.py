from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

# 設定資料檔的路徑
DATA_FILE = "songs_data.json"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"updated_at": "讀取錯誤", "songs": []})
    else:
        # 如果檔案還沒產生
        return jsonify({"updated_at": "等待爬蟲執行中...", "songs": []})

if __name__ == '__main__':
    print("網頁伺服器啟動中... 請在瀏覽器輸入 http://127.0.0.1:5000")
    app.run(debug=True, port=5000)