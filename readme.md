這是一份完整的專案說明文件，整合了我們討論過的**Python 爬蟲腳本**、**前端網頁**以及**GitHub 自動化部署流程**。

你可以將此內容存為 `README.md`，或是當作你的專案維護手冊。

-----

# 🎵 K-Pop 新歌雷達 (Genie Tracker) - 專案手冊

這是一個全自動化的 K-Pop 新歌追蹤系統。

  * **後端**：Python 腳本每日定時爬取 Genie 榜單，保留 90 天內的資料，並自動同步到 GitHub。
  * **前端**：純靜態 HTML/JS 網頁，支援 Dark Mode、QWER 應援色變色、日期分組顯示。
  * **部署**：使用 GitHub Pages 免費託管。

-----

## 📂 檔案結構

請確保你的電腦資料夾內**只有**以下檔案（`app.py` 和 `templates/` 資料夾請刪除）：

```text
Music-tracker/
├── scheduler.py      # 主程式 (爬蟲 + 自動上傳)
├── index.html        # 前端網頁
└── songs_data.json   # 資料庫 (由程式自動產生，若無可忽略)
```

-----

## 1️⃣ Python 主程式 (`scheduler.py`)

此程式負責爬取資料、刪除過期 (90天前) 的舊歌，並自動執行 Git 指令上傳。

```python
import time
import schedule
import json
import requests
import os
import subprocess
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# === 設定區 ===
MY_ARTISTS = [
    "10CM", "(G)I-DLE", "aespa", "AKMU", "Apink", "BABYMONSTER", "BLACKPINK", "BOL4", 
    "BTS", "Chung Ha", "DAY6", "Dreamcatcher", "EVERGLOW", "FIFTY FIFTY", "fromis_9", 
    "GFRIEND", "IU", "IVE", "LE SSERAFIM", "Mamamoo", "NewJeans", "NMIXX", "OH MY GIRL", 
    "QWER", "Red Velvet", "STAYC", "Taeyeon", "TWICE", "VIVIZ", "ITZY" 
    # (請自行在此處增減你的藝人名單)
]

DATA_FILE = "songs_data.json"
KEEP_DAYS = 90  # ✅ 資料保留 90 天

NAME_MAPPING = {}

# === Git 自動上傳函式 ===
def upload_to_github():
    print("🚀 準備上傳更新到 GitHub...")
    try:
        subprocess.run(["git", "add", DATA_FILE], check=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Auto update data: {timestamp}"
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ GitHub 上傳成功！")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in str(e) or e.returncode == 1:
            print("👌 檔案無變更，跳過上傳。")
        else:
            print(f"❌ Git 操作失敗: {e}")
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")

def load_existing_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "songs" in data: return data["songs"]
                return []
        except: return []
    return []

def scrape_job():
    print(f"[{datetime.now()}] 啟動排程：檢查新歌與清理舊資料...")
    existing_songs = load_existing_data()
    existing_links = {song['link'] for song in existing_songs}
    new_songs = []
    
    try:
        url = "https://www.genie.co.kr/newest/song"
        headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        song_list = soup.select("table.list-wrap > tbody > tr")

        for song in song_list:
            try:
                artist_elem = song.select_one("a.artist")
                original_artist_name = artist_elem.text.strip() if artist_elem else ""
                
                is_target = any(target.lower() in original_artist_name.lower() for target in MY_ARTISTS)
                if not is_target: continue 

                link_id = song['songid']
                link = f"https://www.genie.co.kr/detail/songInfo?xgnm={link_id}"
                if link in existing_links: continue

                display_artist_name = original_artist_name
                # (如有需要可在這裡加入 NAME_MAPPING 邏輯)

                album_elem = song.select_one("a.albumtitle")
                title = album_elem.text.strip() if album_elem else "未知專輯"
                if "TITLE" in title: title = title.replace("TITLE", "").strip()
                if "19금" in title: title = title.replace("19금", "").strip()

                img_elem = song.select_one("a.cover img")
                img_src = "https:" + img_elem['src'] if img_elem else ""

                new_songs.append({
                    "artist": display_artist_name,
                    "title": title,
                    "image": img_src,
                    "link": link,
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                print(f"   -> 🎉 發現新歌：{display_artist_name} - {title}")
            except: continue
    except Exception as e:
        print(f"⚠️ 爬蟲連線失敗: {e}")

    # === 清理與存檔 ===
    full_song_list = new_songs + existing_songs
    cutoff_date = datetime.now() - timedelta(days=KEEP_DAYS)
    final_list = []
    
    for song in full_song_list:
        try:
            if datetime.strptime(song['found_at'], "%Y-%m-%d %H:%M") > cutoff_date:
                final_list.append(song)
        except: final_list.append(song)

    data_to_save = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "songs": final_list
    }
    
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"[{datetime.now()}] 本地存檔完成。目前總數: {len(final_list)}")
        upload_to_github() # 觸發上傳
    except Exception as e:
        print(f"存檔失敗: {e}")

if __name__ == "__main__":
    print(f"=== Genie 爬蟲機器人啟動 (資料保留 {KEEP_DAYS} 天) ===")
    scrape_job() # 啟動時先跑一次
    
    schedule.every().day.at("11:00").do(scrape_job)
    schedule.every().day.at("17:00").do(scrape_job)
    schedule.every().day.at("23:00").do(scrape_job)

    while True:
        schedule.run_pending()
        time.sleep(60)
```

-----

## 2️⃣ 前端網頁 (`index.html`)

此檔案負責讀取 JSON 並顯示。特色：自動按日期分組、QWER 變色特效、防止快取。

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genie Tracker</title>
    <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@600;800&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212; --bg-header: #000000;
            --card-bg: #181818; --card-border: #282828; --card-hover-bg: #222222;
            --accent-color: #5CC9F5;
            --text-main: #FFFFFF; --text-sub: #B0B0B0; --input-bg: #2C2C2C;
        }
        body { font-family: 'Open Sans', sans-serif; background-color: var(--bg-main); color: var(--text-main); margin: 0; padding-top: 70px; transition: color 1.5s ease; }
        header { background-color: var(--bg-header); height: 70px; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; position: fixed; top: 0; left: 0; right: 0; z-index: 1000; border-bottom: 1px solid #1f1f1f; }
        .logo { font-family: 'Barlow', sans-serif; font-weight: 800; font-size: 24px; display: flex; align-items: center; color: var(--text-main); }
        .highlight-text { color: var(--accent-color); transition: color 1.5s ease; margin-right: 4px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 30px; }
        .page-title { font-size: 24px; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .page-title::after { content: ''; display: block; width: 40px; height: 4px; background-color: var(--accent-color); margin-top: 5px; transition: background-color 1.5s ease; }
        .date-header { width: 100%; margin-top: 40px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--card-border); color: var(--text-sub); font-size: 1.2rem; font-weight: 700; font-family: 'Barlow', sans-serif; display: flex; align-items: center; gap: 10px; }
        .date-header span { color: var(--accent-color); transition: color 1.5s ease; }
        .grid-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 24px; margin-bottom: 10px; }
        .card { background-color: var(--card-bg); border: 1px solid var(--card-border); padding: 16px; border-radius: 8px; display: flex; flex-direction: column; text-decoration: none; transition: all 0.3s; position: relative; color: inherit; }
        .img-wrapper { position: relative; width: 100%; aspect-ratio: 1/1; background-color: #111; overflow: hidden; border-radius: 6px; margin-bottom: 12px; }
        .img-wrapper img { width: 100%; height: 100%; object-fit: cover; }
        .card:hover { transform: translateY(-5px); border-color: var(--accent-color); }
        .card:hover .song-title { color: var(--accent-color); }
        .song-title { font-weight: 700; font-size: 15px; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .artist-name { font-size: 13px; color: var(--text-sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .status-msg { text-align: center; padding: 80px; color: var(--text-sub); border: 1px dashed #333; border-radius: 8px; margin-top: 20px; }
        @media (max-width: 600px) { .update-info { display: none; } header { padding: 0 15px; } }
    </style>
</head>
<body>
    <header>
        <div class="logo"><span class="highlight-text">genie</span> tracker</div>
        <div style="font-size: 12px; color: #888;" id="statusText">Connecting...</div>
    </header>
    <div class="container">
        <div class="page-title"><span class="highlight-text">New</span> Releases</div>
        <div id="contentArea"></div>
    </div>
    <script>
        const qwerColors = ['#5CC9F5', '#69DB7C', '#FFFFFF', '#FF85C2'];
        let colorIndex = 0;
        setInterval(() => {
            document.documentElement.style.setProperty('--accent-color', qwerColors[colorIndex]);
            colorIndex = (colorIndex + 1) % qwerColors.length;
        }, 4000);

        let allSongsData = [];
        document.addEventListener('DOMContentLoaded', fetchData);

        async function fetchData() {
            try {
                // 加入 timestamp 防止快取
                const res = await fetch('songs_data.json?t=' + new Date().getTime()); 
                const data = await res.json();
                document.getElementById('statusText').innerText = `Updated: ${data.updated_at}`;
                allSongsData = data.songs || [];
                renderSongs(allSongsData);
            } catch (err) {
                document.getElementById('contentArea').innerHTML = `<div class="status-msg">無法讀取資料 (songs_data.json)</div>`;
            }
        }

        function renderSongs(songs) {
            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = '';
            
            // 過濾 90 天
            const KEEP_DAYS = 90;
            const cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - KEEP_DAYS);
            
            const activeSongs = songs.filter(s => new Date(s.found_at) > cutoffDate);

            if (activeSongs.length === 0) {
                contentArea.innerHTML = `<div class="status-msg">最近 90 天無新資料。</div>`;
                return;
            }

            const sortedSongs = activeSongs.slice().sort((a, b) => new Date(b.found_at) - new Date(a.found_at));
            let lastDateStr = '', currentGrid = null;

            sortedSongs.forEach(song => {
                const dateStr = song.found_at.split(' ')[0];
                if (dateStr !== lastDateStr) {
                    lastDateStr = dateStr;
                    contentArea.innerHTML += `<div class="date-header"><span>📅</span> ${dateStr}</div>`;
                    currentGrid = document.createElement('div');
                    currentGrid.className = 'grid-container';
                    contentArea.appendChild(currentGrid);
                }
                currentGrid.innerHTML += `
                    <a href="${song.link}" target="_blank" class="card">
                        <div class="img-wrapper"><img src="${song.image}" onerror="this.src='https://via.placeholder.com/200'"></div>
                        <div class="song-title">${song.title}</div>
                        <div class="artist-name">${song.artist}</div>
                    </a>`;
            });
        }
    </script>
</body>
</html>
```

-----

## 3️⃣ 初始化與 GitHub 設定 (只需執行一次)

為了確保未來的自動上傳順利，並修正之前的所有錯誤（包含上游分支設定、舊檔案刪除），請**依序**執行以下指令。

在終端機 (Terminal) 中：

1.  **重設 Git 連結** (替換成你的倉庫網址)：

    ```bash
    git remote remove origin
    git remote add origin git@github.com:beetwnus/music-tracker.git
    ```

2.  **整理檔案並確認刪除舊資料**：

    ```bash
    git add -A
    git commit -m "專案重置：包含前端更新與自動化腳本"
    ```

3.  **強制推送 (Force Push)** - 這會解決所有版本衝突：

    ```bash
    git push -f origin main
    ```

4.  **設定上游 (Upstream)** - 解決 Python 自動化報錯的關鍵：

    ```bash
    git push --set-upstream origin main
    ```

-----

## 4️⃣ 開啟 GitHub Pages (讓網頁上線)

1.  進入 GitHub 倉庫頁面 -\> **Settings** -\> **Pages**。
2.  Branch 選擇 `main`，資料夾選 `/(root)`。
3.  儲存後，等待 1 分鐘，上方會出現你的網站網址。

-----

## 5️⃣ 如何日常使用

1.  開啟電腦。
2.  打開終端機，執行：
    ```bash
    python scheduler.py
    ```
3.  **縮小視窗**（不要關閉），程式會每天 11:00, 17:00, 23:00 自動檢查新歌並更新網站。