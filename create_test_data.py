import json
from datetime import datetime, timedelta

# 設定檔案名稱
DATA_FILE = "songs_data.json"

# 取得現在時間
now = datetime.now()

# 偽造三筆資料
test_data = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    "songs": [
        {
            "artist": "aespa",
            "title": "這是今天的歌 (應該保留)",
            "image": "",
            "link": "http://test.com/1",
            # 設定時間為：現在
            "found_at": now.strftime("%Y-%m-%d %H:%M")
        },
        {
            "artist": "IU",
            "title": "這是 89 天前的歌 (應該保留)",
            "image": "",
            "link": "http://test.com/2",
            # 設定時間為：89 天前
            "found_at": (now - timedelta(days=89)).strftime("%Y-%m-%d %H:%M")
        },
        {
            "artist": "QWER",
            "title": "這是 91 天前的歌 (應該被刪除)",
            "image": "",
            "link": "http://test.com/3",
            # 設定時間為：91 天前
            "found_at": (now - timedelta(days=91)).strftime("%Y-%m-%d %H:%M")
        }
    ]
}

# 寫入 json 檔
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(test_data, f, ensure_ascii=False, indent=4)

print(f"已建立測試檔案 {DATA_FILE}，包含 3 筆測試資料。")