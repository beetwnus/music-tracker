import time
import schedule
import json
import requests
import os
import subprocess  # ✅ 新增：用來執行 Git 指令
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================================
# 1. 設定監控藝人名單
# ==========================================
MY_ARTISTS = [
    "10CM", "(G)I-DLE", "A train to autumn", "ADORA", "ADYA", "aespa", "AKMU", "Apink", "ARIAZ", 
    "BABYMONSTER", "BADVILLAIN", "Baek A Yeon", "BBGIRLS", "Billlie", "BLACKPINK", "BOL4", 
    "Brave Girls", "BTS", "BVNDIT", "Choi Yoo jung", "Chung Ha", "CLASS : y", "CLC", "CSR", 
    "DAY6", "Dreamcatcher", "EL7Z UP", "Ellui", "Eunha", "EVERGLOW", "FAVORITE", "FIFTY FIFTY", 
    "fromis_9", "Geenius", "GFRIEND", "Girls Planet 999", "GOT the beat", "GREE", "IU", 
    "KyoungSeo", "Kyung Dasom", "LA LIMA", "LE SSERAFIM", "LEE CHAE YEON", "LEE HI", "LIGHTSUM", 
    "lilli lilli", "Lim Kim", "LIMELIGHT", "Limesoda", "Lisa", "LOONA", "LUNARSOLAR", "LUNCH", 
    "Mamamoo", "mimiirose", "Minnie", "Miyeon", "MOMOLAND", "Moonbyul", "MRCH", "NANA", "NAYEON", 
    "NewJeans", "NMIXX", "NND", "OH MY GIRL", "PIXY", "PLAYBACK", "PRODUCE 48", "Punch", 
    "PURPLE KISS", "Qeendom2", "QWER", "Red Velvet", "RESCENE", "Rocket Punch", "Rolling Quartz", 
    "Rosé", "Rothy", "Ryu Su Jeong", "Saebit", "SECRET NUMBER", "Seo Dahyun", "SEULGI", "Shaun", 
    "SinB", "siso", "Solar", "Somi", "SOOJIN", "Soyeon", "STAYC", "Suzy", "SWAN", "T-ara", 
    "TAEYEON", "TRI.BE", "tripleS", "TWICE", "TZUYU", "Umji", "VIVIZ", "Weeekly", "Weki Meki", 
    "Wendy", "Wheein", "WINTER", "WJSN", "Woo Yerin", "woo!ah!", "WSG Wannabe", "X1", "XG", 
    "Yein", "YENA", "Yerin", "YongYong", "YooA", "Younha", "Yuju", "Yunsae", "Yuqi"
]

# ==========================================
# 2. 其他設定
# ==========================================
DATA_FILE = "songs_data.json"
KEEP_DAYS = 90

NAME_MAPPING = {}

# ==========================================
# ✅ 新增：Git 自動上傳函式
# ==========================================
def upload_to_github():
    print("🚀 準備上傳更新到 GitHub...")
    try:
        # 1. 加入檔案 (只加入 json 檔，避免動到其他東西)
        subprocess.run(["git", "add", DATA_FILE], check=True)
        
        # 2. 提交變更 (Commit)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Auto update data: {timestamp}"
        # 注意：如果檔案沒變化，commit 會報錯，所以這裡用 try 忽略沒變化的情況
        subprocess.run(["git", "commit", "-m", message], check=True)
        
        # 3. 推送 (Push)
        subprocess.run(["git", "push"], check=True)
        print("✅ GitHub 上傳成功！")
        
    except subprocess.CalledProcessError as e:
        # 如果是 commit 失敗（通常是因為沒有新變更），我們不當作錯誤
        if "nothing to commit" in str(e) or e.returncode == 1:
            print("👌 檔案無變更，跳過上傳。")
        else:
            print(f"❌ Git 操作失敗 (請確認有設定免密碼登入): {e}")
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")

def load_existing_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "songs" in data: return data["songs"]
                return []
        except:
            return []
    return []

def scrape_job():
    print(f"[{datetime.now()}] 啟動排程：檢查新歌與清理舊資料...")
    
    existing_songs = load_existing_data()
    existing_links = {song['link'] for song in existing_songs}
    new_songs = []
    
    try:
        url = "https://www.genie.co.kr/newest/song"
        headers = { "User-Agent": "Mozilla/5.0..." } # (省略長字串以保持簡潔)
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        song_list = soup.select("table.list-wrap > tbody > tr")

        for song in song_list:
            try:
                artist_elem = song.select_one("a.artist")
                original_artist_name = artist_elem.text.strip() if artist_elem else "未知藝人"

                is_target = False
                for target in MY_ARTISTS:
                    if target.lower() in original_artist_name.lower():
                        is_target = True
                        break
                
                if not is_target: continue 

                link_id = song['songid']
                link = f"https://www.genie.co.kr/detail/songInfo?xgnm={link_id}"

                if link in existing_links: continue

                display_artist_name = original_artist_name
                for key_word, custom_name in NAME_MAPPING.items():
                    if key_word.lower() in original_artist_name.lower():
                        display_artist_name = custom_name
                        break

                album_elem = song.select_one("a.albumtitle")
                title = album_elem.text.strip() if album_elem else "未知專輯"
                
                if "TITLE" in title: title = title.replace("TITLE", "").strip()
                if "19금" in title: title = title.replace("19금", "").strip()

                img_elem = song.select_one("a.cover img")
                img_src = "https:" + img_elem['src'] if img_elem else ""

                new_song = {
                    "artist": display_artist_name,
                    "title": title,
                    "image": img_src,
                    "link": link,
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                new_songs.append(new_song)
                print(f"   -> 🎉 發現新歌：{display_artist_name} - {title}")

            except Exception as e:
                continue

    except Exception as e:
        print(f"⚠️ 爬蟲連線失敗: {e}")

    full_song_list = new_songs + existing_songs
    cutoff_date = datetime.now() - timedelta(days=KEEP_DAYS)
    final_list = []
    deleted_count = 0
    
    for song in full_song_list:
        try:
            song_date = datetime.strptime(song['found_at'], "%Y-%m-%d %H:%M")
            if song_date > cutoff_date:
                final_list.append(song)
            else:
                deleted_count += 1
        except ValueError:
            final_list.append(song)

    data_to_save = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "songs": final_list
    }
    
    try:
        # 1. 寫入本地檔案
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            
        print(f"[{datetime.now()}] 本地存檔完成 (新增:{len(new_songs)}, 刪除:{deleted_count})")
        
        # 2. ✅ 呼叫上傳 GitHub 功能
        upload_to_github()
        
    except Exception as e:
        print(f"存檔失敗: {e}")

if __name__ == "__main__":
    print(f"=== Genie 爬蟲機器人啟動 (含 GitHub 自動同步) ===")
    
    scrape_job()
    
    print("已設定排程：每天 11:00, 17:00, 23:00 自動更新")
    schedule.every().day.at("11:00").do(scrape_job)
    schedule.every().day.at("17:00").do(scrape_job)
    schedule.every().day.at("23:00").do(scrape_job)

    while True:
        schedule.run_pending()
        time.sleep(60)