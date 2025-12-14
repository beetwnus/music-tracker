import time
import schedule
import json
import requests
import os
import subprocess
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================================
# 1. 設定監控藝人名單 (你的本命區)
# ==========================================
MY_ARTISTS = [
    "자정", "(G)I-DLE", "A train to autumn", "ADORA", "ADYA", "aespa", "AKMU", "Apink", "ARIAZ", 
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

DATA_FILE = "songs_data.json"
NAME_MAPPING = {}

# ==========================================
# Git 自動上傳
# ==========================================
def upload_to_github():
    print("🚀 準備上傳更新到 GitHub...")
    try:
        subprocess.run(["git", "add", DATA_FILE], check=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Auto update: {timestamp}"
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push", "-f"], check=True)
        print("✅ GitHub 上傳成功！")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in str(e) or e.returncode == 1:
            print("👌 檔案無變更，跳過上傳。")
        else:
            print(f"❌ Git 上傳發生錯誤: {e}")
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
    print(f"[{datetime.now()}] 啟動排程：掃描所有新發行...")
    
    existing_songs = load_existing_data()
    existing_links = {song['link'] for song in existing_songs}
    new_songs = []
    
    try:
        url = "https://www.genie.co.kr/newest/song"
        headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        song_list = soup.select("table.list-wrap > tbody > tr")

        for song in song_list:
            try:
                artist_elem = song.select_one("a.artist")
                original_artist_name = artist_elem.text.strip() if artist_elem else "未知藝人"

                # ✅ 修改點 1：不再跳過，而是標記是否為「我的藝人」
                is_tracked = False
                for target in MY_ARTISTS:
                    if target.lower() in original_artist_name.lower():
                        is_tracked = True
                        break
                
                # 這裡刪除了 "if not is_tracked: continue" 讓程式抓取所有人

                link_id = song['songid']
                link = f"https://www.genie.co.kr/detail/songInfo?xgnm={link_id}"

                if link in existing_links: continue

                display_artist_name = original_artist_name
                # 只對我的藝人做名稱對應 (非追蹤藝人維持原名)
                if is_tracked:
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
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "is_tracked": is_tracked  # ✅ 新增：標記是否為追蹤藝人
                }
                
                new_songs.append(new_song)
                
                # Log 稍微區分一下顯示
                if is_tracked:
                    print(f"   -> ⭐ 發現關注新歌：{display_artist_name} - {title}")
                else:
                    print(f"   -> 發現其他新歌：{display_artist_name} - {title}")

            except Exception as e:
                continue

    except Exception as e:
        print(f"⚠️ 爬蟲連線失敗: {e}")

    full_song_list = new_songs + existing_songs
    
    # ✅ 修改點 2：設定雙重過濾日期
    now = datetime.now()
    cutoff_90 = now - timedelta(days=90) # 追蹤的保留 90 天
    cutoff_1 = now - timedelta(days=1)   # 沒追蹤的保留 1 天 (24小時)
    
    final_list = []
    
    for song in full_song_list:
        try:
            song_date = datetime.strptime(song['found_at'], "%Y-%m-%d %H:%M")
            is_my_artist = song.get('is_tracked', False) # 取得標記，預設為 False
            
            # 邏輯：(是我的藝人 且 在90天內) 或 (不是我的藝人 且 在1天內)
            if (is_my_artist and song_date > cutoff_90) or (not is_my_artist and song_date > cutoff_1):
                final_list.append(song)
                
        except ValueError:
            final_list.append(song)

    data_to_save = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "songs": final_list
    }
    
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"[{datetime.now()}] 存檔完成。總數: {len(final_list)}")
        upload_to_github()
    except Exception as e:
        print(f"存檔失敗: {e}")

if __name__ == "__main__":
    print(f"=== Genie 全局爬蟲啟動 (關注藝人90天 / 其他1天) ===")
    scrape_job()
    
    schedule.every().day.at("11:00").do(scrape_job)
    schedule.every().day.at("17:00").do(scrape_job)
    schedule.every().day.at("23:00").do(scrape_job)

    while True:
        schedule.run_pending()
        time.sleep(60)