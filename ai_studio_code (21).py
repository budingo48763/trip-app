import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
import random
import json
import base64

# --- 嘗試匯入進階套件 ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    CLOUD_AVAILABLE = True
except ImportError:
    CLOUD_AVAILABLE = False

try:
    import folium
    from streamlit_folium import st_folium
    from geopy.geocoders import Nominatim
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False

try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# -------------------------------------
# 1. 系統設定 & 主題
# -------------------------------------
st.set_page_config(page_title="2026 旅程規劃 Pro", page_icon="✈️", layout="centered", initial_sidebar_state="collapsed")

THEMES = {
    "⛩️ 京都緋紅 (預設)": {"bg": "#FDFCF5", "card": "#FFFFFF", "text": "#2B2B2B", "primary": "#8E2F2F", "secondary": "#D6A6A6", "sub": "#666666"},
    "🌫️ 莫蘭迪·霧藍": {"bg": "#F0F4F8", "card": "#FFFFFF", "text": "#243B53", "primary": "#486581", "secondary": "#BCCCDC", "sub": "#627D98"},
    "🌿 莫蘭迪·鼠尾草": {"bg": "#F1F5F1", "card": "#FFFFFF", "text": "#2C3E2C", "primary": "#5F7161", "secondary": "#AFC0B0", "sub": "#506050"},
    "🍂 莫蘭迪·焦糖奶茶": {"bg": "#FAF6F1", "card": "#FFFFFF", "text": "#4A3B32", "primary": "#9C7C64", "secondary": "#E0D0C5", "sub": "#7D6556"}
}

# -------------------------------------
# 2. 核心功能
# -------------------------------------

# --- 收據分析 (自動辨識多筆) ---
def analyze_receipt_image(image_file):
    if not GEMINI_AVAILABLE:
        return [{"name": "模擬-飯糰", "price": 130}, {"name": "模擬-茶", "price": 150}]
    
    if "GEMINI_API_KEY" not in st.secrets:
        return [{"name": "請設定 API Key", "price": 0}]

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        img = Image.open(image_file)
        
        prompt = """
        你是一個旅遊記帳助手。請分析這張收據圖片。
        任務：
        1. 提取所有「商品名稱」與「金額」。
        2. 將商品名稱翻譯成繁體中文。
        3. 排除小計、消費稅、找零、支付方式等非商品項目。
        4. 回傳 JSON Array，格式：[{"name": "商品名", "price": 100}, ...]
        5. price 必須是整數 (Integer)。不要輸出 Markdown 標記。
        """

        priority_models = [
            'models/gemini-2.0-flash',
            'models/gemini-2.0-flash-exp',
            'models/gemini-1.5-flash',
            'models/gemini-1.5-pro',
            'models/gemini-pro-vision'
        ]
        
        # 自動選擇模型
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except: pass

        target_model = 'models/gemini-1.5-flash'
        for candidate in priority_models:
            if candidate in available_models:
                target_model = candidate
                break
        
        model = genai.GenerativeModel(target_model)
        response = model.generate_content([prompt, img])
        
        text = response.text.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "")
        
        data = json.loads(text)
        if isinstance(data, dict): return [data]
        return data

    except Exception:
        return [{"name": "分析失敗", "price": 0}]

# --- 地理編碼 ---
@st.cache_data
def get_lat_lon(location_name):
    if not MAP_AVAILABLE: return None
    try:
        geolocator = Nominatim(user_agent="trip_planner_v15")
        location = geolocator.geocode(location_name)
        if location: return (location.latitude, location.longitude)
    except: return None
    return None

# --- 雲端 ---
def get_cloud_connection():
    if not CLOUD_AVAILABLE: return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
        client = gspread.authorize(creds)
        return client
    except: return None

def save_to_cloud(json_str):
    client = get_cloud_connection()
    if client:
        try:
            sheet = client.open("TripPlanDB").sheet1 
            sheet.update_cell(1, 1, json_str)
            return True, "儲存成功"
        except Exception as e: return False, str(e)
    return False, "連線失敗"

def load_from_cloud():
    client = get_cloud_connection()
    if client:
        try:
            return client.open("TripPlanDB").sheet1.cell(1, 1).value
        except: return None
    return None

class WeatherService:
    WEATHER_ICONS = {"Sunny": "☀️", "Cloudy": "☁️", "Rainy": "🌧️", "Snowy": "❄️"}
    @staticmethod
    def get_forecast(location, date_obj):
        random.seed(f"{location}{date_obj.strftime('%Y%m%d')}")
        base = 20 if date_obj.month not in [12,1,2] else 5
        cond = random.choice(["Sunny", "Cloudy", "Rainy"])
        desc = {"Sunny": "晴時多雲", "Cloudy": "陰天", "Rainy": "有雨", "Snowy": "降雪"}
        return {"high": base+5, "low": base-3, "icon": WeatherService.WEATHER_ICONS[cond], "desc": desc.get(cond, cond), "raw": cond}

def get_packing_recommendations(trip_data, start_date):
    recs = set()
    has_rain = False
    min_temp = 100
    for day, items in trip_data.items():
        loc = items[0]['loc'] if items else "City"
        w = WeatherService.get_forecast(loc, start_date + timedelta(days=day-1))
        if w['raw'] in ["Rainy", "Snowy"]: has_rain = True
        min_temp = min(min_temp, w['low'])
    if has_rain: recs.add("☔ 雨具")
    if min_temp < 15: recs.add("🧥 外套")
    else: recs.add("🧢 防曬")
    return list(recs)

def add_expense_callback(item_id, day_num):
    n = st.session_state.get(f"new_exp_n_{item_id}", "")
    p = st.session_state.get(f"new_exp_p_{item_id}", 0)
    if n and p > 0:
        item = next((x for x in st.session_state.trip_data[day_num] if x['id'] == item_id), None)
        if item:
            if "expenses" not in item: item["expenses"] = []
            item['expenses'].append({"name": n, "price": p})
            item['cost'] = sum(x['price'] for x in item['expenses'])
            st.session_state[f"new_exp_n_{item_id}"] = ""
            st.session_state[f"new_exp_p_{item_id}"] = 0

def get_single_map_link(loc):
    return loc if loc.startswith("http") else f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(loc)}"

def generate_google_nav_link(origin, dest):
    return f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(dest)}&travelmode=transit"

def generate_google_map_route(items):
    valid = [urllib.parse.quote(i['loc']) for i in items if i.get('loc')]
    return f"https://www.google.com/maps/dir/{'/'.join(valid)}" if valid else "#"

def process_excel_upload(file):
    try:
        df = pd.read_excel(file)
        data = {}
        for _, row in df.iterrows():
            d = int(row['Day'])
            if d not in data: data[d] = []
            data[d].append({
                "id": int(time.time()*1000)+_, "time": str(row['Time']), "title": str(row['Title']),
                "loc": str(row.get('Location','')), "cost": int(row.get('Cost',0)), 
                "note": str(row.get('Note','')), "expenses": []
            })
        st.session_state.trip_data = data
        st.session_state.trip_days_count = max(data.keys())
        st.rerun()
    except: st.error("格式錯誤")

# -------------------------------------
# 3. 初始化
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "target_country" not in st.session_state: st.session_state.target_country = "日本"
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "⛩️ 京都緋紅 (預設)"
if "start_date" not in st.session_state: st.session_state.start_date = datetime(2026, 1, 17)
if "wishlist" not in st.session_state: st.session_state.wishlist = [{"id":901, "title":"HARBS", "loc":"京都", "note":"千層蛋糕"}]
if "shopping_list" not in st.session_state: st.session_state.shopping_list = pd.DataFrame(columns=["對象","商品名稱","預算(¥)","已購買"])

cur_theme = THEMES[st.session_state.selected_theme_name]

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id": 101, "time": "10:00", "title": "抵達機場", "loc": "關西機場", "cost": 0, "note": "入境", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 45}],
        2: [{"id": 201, "time": "09:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "note": "", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 20}],
        3: [], 4: [], 5: []
    }

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {"outbound": {"date":"1/17","code":"JX821","dep":"10:00","arr":"13:30","dep_loc":"TPE","arr_loc":"KIX"}, "inbound": {"date":"1/22","code":"JX822","dep":"15:00","arr":"17:10","dep_loc":"KIX","arr_loc":"TPE"}}

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [{"id":1, "name":"KOKO HOTEL", "range":"D1-D3", "date":"1/17-1/19", "addr":"京都", "link":""}]

if "checklist" not in st.session_state:
    st.session_state.checklist = {"證件":{"護照":False}, "電子":{"網卡":False}, "衣物":{"外套":False}, "生活":{"牙刷":False}}

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船", "✈️ 飛機"]

SURVIVAL_PHRASES = {
    "日本": {
        "招呼": [("你好", "こんにちは"), ("謝謝", "ありがとう"), ("不好意思", "すみません")],
        "點餐": [("請給我這個", "これをください"), ("買單", "お会計お願いします"), ("多少錢", "いくらですか")],
        "交通": [("在哪裡", "どこですか"), ("車站", "駅"), ("廁所", "トイレ")],
        "購物": [("免稅", "免税できますか"), ("袋子", "袋をください")],
        "緊急": [("救命", "助けて"), ("不舒服", "具合が悪いです"), ("迷路", "迷子になりました")]
    },
    "韓國": {
        "招呼": [("你好", "안녕하세요"), ("謝謝", "감사합니다")],
        "點餐": [("請給我這個", "이거 주세요"), ("買單", "계산해 주세요")],
        "交通": [("在哪裡", "어디에요"), ("洗手間", "화장실")],
        "購物": [("多少錢", "얼마예요"), ("打折", "깎아 주세요")],
        "緊急": [("救命", "도와주세요"), ("警察", "경찰")]
    },
    "泰國": {
        "招呼": [("你好", "Sawasdee"), ("謝謝", "Khop khun")],
        "點餐": [("多少錢", "Tao rai"), ("不辣", "Mai pet")],
        "交通": [("廁所", "Hong nam"), ("機場", "Sanam bin")],
        "購物": [("太貴", "Paeng mak"), ("便宜點", "Lot noi")],
        "緊急": [("救命", "Chuay duay"), ("去醫院", "Bai rong paya ban")]
    }
}

# -------------------------------------
# 4. CSS
# -------------------------------------
# CSS 變數
c_bg, c_text, c_card, c_primary, c_sub, c_sec = cur_theme['bg'], cur_theme['text'], cur_theme['card'], cur_theme['primary'], cur_theme['sub'], cur_theme['secondary']

main_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=Inter:wght@400;600&display=swap');
.stApp {{ background-color: {c_bg} !important; color: {c_text} !important; font-family: 'Inter', sans-serif !important; }}
[data-testid="stSidebarCollapsedControl"], footer {{ display: none !important; }}
header[data-testid="stHeader"] {{ height: 0 !important; background: transparent !important; }}
.apple-card {{
    background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px); border-radius: 18px;
    padding: 18px; margin-bottom: 0px; border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 4px 15px rgba(0,0,0,0.04);
}}
.apple-weather-widget {{
    background: linear-gradient(135deg, {c_primary} 0%, {c_text} 150%); color: white;
    padding: 15px 20px; border-radius: 20px; margin-bottom: 25px;
    display: flex; align-items: center; justify-content: space-between; box-shadow: 0 8px 20px rgba(0,0,0,0.15);
}}
.trans-card {{
    background: #FFF; border-radius: 12px; padding: 10px 15px; margin: 10px 0 10px 50px;
    border: 1px solid #E0E0E0; display: flex; justify-content: space-between; align-items: center;
}}
.trans-tag {{ font-size: 0.75rem; padding: 3px 8px; border-radius: 6px; background: #F0F4F8; color: #486581; }}
.info-card {{ background: {c_card}; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid #F0F0F0; }}
.info-tag {{ background: {c_bg}; color: {c_sub}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
div[data-testid="stRadio"] > div {{ background-color: {c_sec}; padding: 4px; border-radius: 12px; overflow-x:
