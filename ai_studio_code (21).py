import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
import random
import json

# --- 嘗試匯入進階套件 (雲端 & 地圖) ---
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

# -------------------------------------
# 1. 系統設定 & 主題定義
# -------------------------------------
st.set_page_config(page_title="2026 旅程規劃 Pro", page_icon="✈️", layout="centered", initial_sidebar_state="collapsed")

# 🎨 主題配色庫
THEMES = {
    "⛩️ 京都緋紅 (預設)": {
        "bg": "#FDFCF5", "card": "#FFFFFF", "text": "#2B2B2B", "primary": "#8E2F2F", "secondary": "#D6A6A6", "sub": "#666666"
    },
    "🌫️ 莫蘭迪·霧藍": {
        "bg": "#F0F4F8", "card": "#FFFFFF", "text": "#243B53", "primary": "#486581", "secondary": "#BCCCDC", "sub": "#627D98"
    },
    "🌿 莫蘭迪·鼠尾草": {
        "bg": "#F1F5F1", "card": "#FFFFFF", "text": "#2C3E2C", "primary": "#5F7161", "secondary": "#AFC0B0", "sub": "#506050"
    },
    "🍂 莫蘭迪·焦糖奶茶": {
        "bg": "#FAF6F1", "card": "#FFFFFF", "text": "#4A3B32", "primary": "#9C7C64", "secondary": "#E0D0C5", "sub": "#7D6556"
    }
}

# -------------------------------------
# 2. 核心功能函數
# -------------------------------------

# --- 地理編碼 (新增：地址轉經緯度) ---
@st.cache_data
def get_lat_lon(location_name):
    if not MAP_AVAILABLE: return None
    try:
        # 使用 Nominatim (OpenStreetMap)
        geolocator = Nominatim(user_agent="trip_planner_app_demo")
        location = geolocator.geocode(location_name)
        if location:
            return (location.latitude, location.longitude)
    except:
        return None
    return None

# --- 雲端連線 ---
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
    except:
        return None

def save_to_cloud(json_str):
    client = get_cloud_connection()
    if client:
        try:
            sheet = client.open("TripPlanDB").sheet1 
            sheet.update_cell(1, 1, json_str)
            return True, "儲存成功！"
        except Exception as e:
            return False, f"寫入失敗: {e}"
    return False, "連線失敗"

def load_from_cloud():
    client = get_cloud_connection()
    if client:
        try:
            sheet = client.open("TripPlanDB").sheet1
            return sheet.cell(1, 1).value
        except:
            return None
    return None

class WeatherService:
    WEATHER_ICONS = {"Sunny": "☀️", "Cloudy": "☁️", "Rainy": "🌧️", "Snowy": "❄️"}
    @staticmethod
    def get_forecast(location, date_obj):
        seed_str = f"{location}{date_obj.strftime('%Y%m%d')}"
        random.seed(seed_str)
        base_temp = 20 if date_obj.month not in [12,1,2] else 5
        high = base_temp + random.randint(0, 5)
        low = base_temp - random.randint(3, 8)
        cond = random.choice(["Sunny", "Cloudy", "Rainy"])
        desc_map = {"Sunny": "晴時多雲", "Cloudy": "陰天", "Rainy": "有雨", "Snowy": "降雪"}
        return {"high": high, "low": low, "icon": WeatherService.WEATHER_ICONS[cond], "desc": desc_map.get(cond, cond), "raw": cond}

def get_packing_recommendations(trip_data, start_date):
    recommendations = set()
    has_rain = False
    min_temp = 100
    for day, items in trip_data.items():
        loc = items[0]['loc'] if items else "City"
        w = WeatherService.get_forecast(loc, start_date + timedelta(days=day-1))
        if w['raw'] in ["Rainy", "Snowy"]: has_rain = True
        min_temp = min(min_temp, w['low'])
    
    if has_rain: recommendations.update(["☔ 折疊傘/雨衣", "👞 防水噴霧"])
    if min_temp < 12: recommendations.update(["🧣 圍巾", "🧥 保暖外套", "🧤 手套"])
    elif min_temp < 20: recommendations.update(["🧥 薄外套"])
    if min_temp > 25: recommendations.update(["🕶️ 太陽眼鏡", "🧢 帽子", "🧴 防曬"])
    return list(recommendations)

def add_expense_callback(item_id, day_num):
    name_key = f"new_exp_n_{item_id}"
    price_key = f"new_exp_p_{item_id}"
    name = st.session_state.get(name_key, "")
    price = st.session_state.get(price_key, 0)
    if name and price > 0:
        target_item = next((x for x in st.session_state.trip_data[day_num] if x['id'] == item_id), None)
        if target_item:
            if "expenses" not in target_item: target_item["expenses"] = []
            target_item['expenses'].append({"name": name, "price": price})
            target_item['cost'] = sum(x['price'] for x in target_item['expenses'])
            st.session_state[name_key] = ""
            st.session_state[price_key] = 0

def get_single_map_link(location):
    if not location: return "#"
    if location.startswith("http"): return location
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(location)}"

def generate_google_nav_link(origin, dest, mode="transit"):
    """生成兩點間的 Google Maps 導航連結"""
    if not origin or not dest: return "#"
    base = "https://www.google.com/maps/dir/?api=1"
    return f"{base}&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(dest)}&travelmode={mode}"

def generate_google_map_route(items):
    valid_locs = [item['loc'] for item in items if item.get('loc') and item['loc'].strip()]
    if len(valid_locs) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    encoded_locs = [urllib.parse.quote(loc) for loc in valid_locs]
    return base_url + "/".join(encoded_locs)

def process_excel_upload(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        new_trip_data = {}
        for _, row in df.iterrows():
            day = int(row['Day'])
            if day not in new_trip_data: new_trip_data[day] = []
            time_str = row['Time'].strftime("%H:%M") if isinstance(row['Time'], (datetime, pd.Timestamp)) else str(row['Time'])
            item = {
                "id": int(time.time() * 1000) + _, 
                "time": time_str,
                "title": str(row['Title']),
                "loc": str(row.get('Location', '')),
                "cost": int(row.get('Cost', 0)) if pd.notnull(row.get('Cost')) else 0,
                "cat": "other",
                "note": str(row.get('Note', '')),
                "expenses": [],
                "trans_mode": "📍 移動",
                "trans_min": 30
            }
            new_trip_data[day].append(item)
        st.session_state.trip_data = new_trip_data
        st.session_state.trip_days_count = max(new_trip_data.keys())
        st.toast("✅ 行程匯入成功！")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"匯入失敗: {e}")

# -------------------------------------
# 3. 初始化 & 資料
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "target_country" not in st.session_state: st.session_state.target_country = "日本"
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "⛩️ 京都緋紅 (預設)"
if "start_date" not in st.session_state: st.session_state.start_date = datetime(2026, 1, 17)

# 願望清單
if "wishlist" not in st.session_state:
    st.session_state.wishlist = [
        {"id": 901, "title": "HARBS 千層蛋糕", "loc": "大丸京都店", "note": "必吃水果千層"},
        {"id": 902, "title": " % Arabica 咖啡", "loc": "嵐山", "note": "網美打卡點"}
    ]

# 購物清單
if "shopping_list" not in st.session_state:
    st.session_state.shopping_list = pd.DataFrame(columns=["對象", "商品名稱", "預算(¥)", "已購買"])

current_theme = THEMES[st.session_state.selected_theme_name]

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "time": "10:00", "title": "抵達關西機場", "loc": "關西機場", "cost": 0, "cat": "trans", "note": "入境審查", "expenses": [], "trans_mode": "🚆 Skyliner", "trans_min": 45},
            {"id": 102, "time": "13:00", "title": "京都車站 Check-in", "loc": "KOKO HOTEL 京都", "cost": 0, "cat": "stay", "note": "寄放行李", "expenses": [], "trans_mode": "🚌 巴士", "trans_min": 20},
            {"id": 103, "time": "15:00", "title": "錦市場", "loc": "錦市場", "cost": 2000, "cat": "food", "note": "吃午餐", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 104, "time": "18:00", "title": "鴨川散步", "loc": "鴨川", "cost": 0, "cat": "spot", "note": "夜景", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
        ],
        2: [
            {"id": 201, "time": "09:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "cat": "spot", "note": "清水舞台", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 20},
            {"id": 202, "time": "11:00", "title": "三年坂", "loc": "三年坂", "cost": 1000, "cat": "spot", "note": "買伴手禮", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 203, "time": "13:00", "title": "八坂神社", "loc": "八坂神社", "cost": 0, "cat": "spot", "note": "祈福", "expenses": [], "trans_mode": "🚌 巴士", "trans_min": 30}
        ],
        3: [], 4: [], 5: []
    }

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {
        "outbound": {"date": "1/17", "code": "JX821", "dep": "10:00", "arr": "13:30", "dep_loc": "桃機 T1", "arr_loc": "關西機場"},
        "inbound": {"date": "1/22", "code": "JX822", "dep": "15:00", "arr": "17:10", "dep_loc": "關西機場", "arr_loc": "桃機 T1"}
    }

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [
        {"id": 1,
