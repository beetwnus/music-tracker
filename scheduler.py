import json
import requests
import os
import re  # ✅ 新增正則表達式模組
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 設定監控藝人名單
# ==========================================
MY_ARTISTS = [
    "(G)I-DLE", "A train to autumn", "ADORA", "ADYA", "aespa", "AKMU", "Apink", "ARIAZ", 
    "BABYMONSTER", "BADVILLAIN", "Baek A Yeon", "BBGIRLS", "Billlie", "BLACKPINK", "BOL4", 
    "Brave Girls", "BTS", "BVNDIT", "Choi Yoo jung", "Chung Ha", "CLASS:y", "CLC", "CSR", 
    "Dreamcatcher", "EL7Z UP", "Ellui", "Eunha", "EVERGLOW", "FAVORITE", "FIFTY FIFTY", 
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
# 工具函式
# ==========================================
def get_taiwan_timezone():
    """回傳台灣時區物件"""
    return timezone(timedelta(hours=8))

def get_taiwan_time():
    """取得台灣時間 (UTC+8)"""
    return datetime.now(get_taiwan_timezone())

def load_existing_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "songs" in data: return data["songs"]
                return []
        except: return []
    return []

# ✅ 新增：智慧比對函式
def is_artist_match(target, text):
    """
    判斷 text 中是否包含 target 藝人。
    針對短英文 (如 IU) 啟用嚴格邊界檢查，避免誤判 (如 XIUMIN 包含 IU)。
    """
    target = target.lower()
    text = text.lower()
    
    # 判斷條件：如果 target 是純英數字 且 長度小於等於 3 (例如 IU, V, X1)
    if len(target) <= 3 and re.match(r'^[a-z0-9]+$', target):
        # 使用 Regex 檢查前後邊界 (前後不能是英文字母或數字)
        # 這樣 IU 就不會對到 XIUMIN，但可以對到 IU(Lee) 或 IU,
        pattern = r'(?:^|[^a-z0-9])' + re.escape(target) + r'(?:$|[^a-z0-9])'
        return re.search(pattern, text) is not None
    
    # 其他情況 (中文、韓文、長英文名) 維持原本的寬鬆包含檢查
    return target in text

# ==========================================
# 主邏輯
# ==========================================
def scrape_job():
    print(f"[{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}] 雲端爬蟲啟動 (Taiwan Time)...")
    
    existing_songs = load_existing_data()
    existing_links = {song['link'] for song in existing_songs}
    new_songs = []
    
    # 1. 爬取新資料
    try:
        url = "https://www.genie.co.kr/newest/song"
        headers = { 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" 
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        song_list = soup.select("table.list-wrap > tbody > tr")

        for song in song_list:
            try:
                artist_elem = song.select_one("a.artist")
                original_artist_name = artist_elem.text.strip() if artist_elem else "未知藝人"

                # ✅ 使用新的比對邏輯
                is_tracked = False
                for target in MY_ARTISTS:
                    if is_artist_match(target, original_artist_name):
                        is_tracked = True
                        break
                
                link_id = song['songid']
                link = f"https://www.genie.co.kr/detail/songInfo?xgnm={link_id}"

                if link in existing_links: continue

                display_artist_name = original_artist_name
                if is_tracked:
                    for key_word, custom_name in NAME_MAPPING.items():
                        if is_artist_match(key_word, original_artist_name):
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
                    "found_at": get_taiwan_time().strftime("%Y-%m-%d %H:%M"),
                    "is_tracked": is_tracked
                }
                new_songs.append(new_song)
                
                log_prefix = "⭐ 關注" if is_tracked else "   其他"
                print(f"   -> {log_prefix}：{display_artist_name} - {title}")

            except Exception as e: continue

    except Exception as e:
        print(f"⚠️ 爬蟲錯誤: {e}")

    # 2. 合併與清理
    full_song_list = new_songs + existing_songs
    
    # 取得現在的台灣時間
    now_tw = get_taiwan_time()
    today_date = now_tw.date()
    
    cutoff_90 = now_tw - timedelta(days=90)
    
    final_list = []
    
    tz_tw = get_taiwan_timezone()

    for song in full_song_list:
        try:
            song_datetime_naive = datetime.strptime(song['found_at'], "%Y-%m-%d %H:%M")
            song_datetime = song_datetime_naive.replace(tzinfo=tz_tw)
            
            song_date = song_datetime.date()
            
            is_my_artist = song.get('is_tracked', False)
            
            if is_my_artist:
                # 規則 A：我的藝人 -> 保留 90 天
                if song_datetime > cutoff_90:
                    final_list.append(song)
            else:
                # 規則 B：其他藝人 -> 只保留「今天」
                if song_date == today_date:
                    final_list.append(song)
                    
        except ValueError:
            final_list.append(song)

    # 3. 存檔
    data_to_save = {
        "updated_at": get_taiwan_time().strftime("%Y-%m-%d %H:%M:%S"),
        "songs": final_list
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 資料已更新。目前資料庫總數: {len(final_list)}")

if __name__ == "__main__":
    scrape_job()
