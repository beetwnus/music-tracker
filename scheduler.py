import json
import requests
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. 設定監控藝人名單
# ==========================================
MY_ARTISTS = [
    "ADORA", "ADYA", "aespa", "AKMU", "Apink",
    "BABYMONSTER", "BADVILLAIN", "Baek A Yeon", "BBGIRLS",
    "Billlie", "BLACKPINK", "BOL4", "BTS", "Choi Yoo jung", 
    "Chung Ha", "CLASS:y", "CSR", "Dreamcatcher", "EL7Z UP", "Ellui", 
    "Eunha", "EVERGLOW", "FIFTY FIFTY", "fromis_9", "Geenius", "GFRIEND",
    "GOT the beat", "Gyubin", "H1-KEY", "Hayeon", "Hearts2Hearts", "Hebi",
    "HUH YUNJIN", "HwaSa", "Hyoyeon", "i-dle", "ILLIT", "ILY:1",
    "ITZY", "IU", "IVE", "izna", "Jennie", "Jeong hyo bean",
    "JIHYO", "JISOO", "JO YURI", "Joy", "Kang Hye Won",
    "KARD", "Kassy", "Kep1er", "KiiiKiii", "Kim Mi Jeong",
    "Kim Sejeong", "KIMDOAH", "KISS OF LIFE", "Kwon Eun Bi",
    "KyoungSeo", "LE SSERAFIM", "LEE CHAE YEON", "LEE HI",
    "LIGHTSUM", "lilli lilli", "Lim Kim", "LIMELIGHT",
    "Lisa", "Mamamoo", "Minnie", "Miyeon", "Moonbyul",
    "MRCH", "NANA", "NAYEON", "NewJeans", "NMIXX", "OH MY GIRL",
    "Punch", "QWER", "Red Velvet", "RESCENE", "Rosé", "Rothy",
    "Ryu Su Jeong", "Saebit", "SECRET NUMBER", "Seo Dahyun",
    "SEULGI", "SinB", "siso", "Solar", "Somi", "SOOJIN",
    "Soyeon", "STAYC", "Suzy", "SWAN", "Taeyeon", "T-ara",
    "TRI.BE", "tripleS", "TWICE", "TZUYU", "Umji",
    "VIVIZ", "Wendy", "Wheein", "WINTER", "WJSN",
    "Woo Yerin", "woo!ah!", "Yein", "YENA", "Yerin",
    "YooA", "Younha", "Yuju", "Yunsae", "Yuqi"
]

DATA_FILE = "songs_data.json"
NAME_MAPPING = {}

# ==========================================
# 工具函式
# ==========================================
def get_taiwan_timezone():
    return timezone(timedelta(hours=8))

def get_taiwan_time():
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

def is_artist_match(target, text):
    target = target.lower()
    text = text.lower()
    if len(target) <= 3 and re.match(r'^[a-z0-9]+$', target):
        pattern = r'(?:^|[^a-z0-9])' + re.escape(target) + r'(?:$|[^a-z0-9])'
        return re.search(pattern, text) is not None
    return target in text

# ==========================================
# 主邏輯
# ==========================================
def scrape_job():
    print(f"[{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}] 雲端爬蟲啟動 (Taiwan Time)...")
    
    existing_songs = load_existing_data()
    existing_links = {song['link'] for song in existing_songs}
    new_songs = []
    
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

    full_song_list = new_songs + existing_songs
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
                if song_datetime > cutoff_90:
                    final_list.append(song)
            else:
                if song_date == today_date:
                    final_list.append(song)
        except ValueError:
            final_list.append(song)

    # 3. 存檔 (✅ 修改點：加入 tracked_artists)
    data_to_save = {
        "updated_at": get_taiwan_time().strftime("%Y-%m-%d %H:%M:%S"),
        "tracked_artists": sorted(MY_ARTISTS), # 自動按字母排序
        "songs": final_list
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 資料已更新。目前資料庫總數: {len(final_list)}")

if __name__ == "__main__":
    scrape_job()
