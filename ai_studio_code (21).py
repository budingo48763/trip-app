import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
import random
import json
import base64

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

# --- Google Gemini 套件 ---
try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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

# --- 收據分析 (多筆明細 + 翻譯 + 排除雜訊) ---
def analyze_receipt_image(image_file):
    """使用 Google Gemini 分析收據，回傳翻譯後的項目清單"""
    
    if not GEMINI_AVAILABLE:
        return [{"name": "模擬-飯糰 (翻譯)", "price": 130}, {"name": "模擬-可樂 (翻譯)", "price": 140}]
    
    if "GEMINI_API_KEY" not in st.secrets:
        return [{"name": "請設定 API Key", "price": 0}]

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        img = Image.open(image_file)
        
        # --- 關鍵 Prompt 修改 ---
        prompt = """
        你是一個專業的旅遊記帳助手。請分析這張收據圖片（通常是日本收據）。
        
        請執行以下任務：
        1. **提取商品**：列出每一個購買的商品項目與其金額。
        2. **翻譯**：將日文商品名稱翻譯成「繁體中文」。
        3. **排除雜訊**：絕對不要包含「小計」、「消費稅」、「合計」、「現計」、「找零(お釣り)」、「點數」、「支付方式(如 Suica, nanaco)」等非商品項目。
        4. **金額處理**：只提取該商品的單行金額（通常日本收據單行金額不含稅，或已有標示，請直接取該行數字即可，不用自己加稅）。
        
        請回傳一個純 JSON Array (List)，格式如下：
        [{"name": "翻譯後的商品名稱", "price": 120}, {"name": "另一項商品", "price": 500}]
        
        注意：price 必須是整數 (Integer)。不要使用 Markdown 標記。
        """

        # 自動尋找可用模型
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except:
            pass

        priority_models = [
            'models/gemini-2.0-flash',
            'models/gemini-2.0-flash-exp',
            'models/gemini-1.5-flash',
            'models/gemini-1.5-flash-latest',
            'models/gemini-1.5-pro',
            'models/gemini-pro-vision'
        ]

        target_model_name = 'models/gemini-1.5-flash'
        for candidate in priority_models:
            if candidate in available_models:
                target_model_name = candidate
                break
        
        model = genai.GenerativeModel(target_model_name)
        response = model.generate_content([prompt, img])
        
        text = response.text.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "")
        
        data = json.loads(text)
        if isinstance(data, dict): return [data]
        return data

    except Exception as e:
        return [{"name": "分析失敗", "price": 0}]

# --- 地理編碼 ---
@st.cache_data
def get_lat_lon(location_name):
    if not MAP_AVAILABLE: return None
    try:
        geolocator = Nominatim(user_agent="trip_planner_app_final_v13")
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

if "wishlist" not in st.session_state:
    st.session_state.wishlist = [
        {"id": 901, "title": "HARBS 千層蛋糕", "loc": "大丸京都店", "note": "必吃水果千層"},
        {"id": 902, "title": " % Arabica 咖啡", "loc": "嵐山", "note": "網美打卡點"}
    ]

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
        {"id": 1, "name": "KOKO HOTEL 京都", "range": "D1-D3 (3泊)", "date": "1/17 - 1/19", "addr": "京都府京都市...", "link": ""},
        {"id": 2, "name": "相鐵 FRESA INN 大阪", "range": "D4-D5 (2泊)", "date": "1/20 - 1/21", "addr": "大阪府大阪市...", "link": ""}
    ]

if "checklist" not in st.session_state:
    st.session_state.checklist = {
        "必要證件": {"護照": False, "機票證明": False, "Visit Japan Web": False, "日幣現金": False},
        "電子產品": {"手機 & 充電線": False, "行動電源": False, "SIM卡 / Wifi機": False, "轉接頭": False},
        "衣物穿搭": {"換洗衣物": False, "睡衣": False, "好走的鞋子": False, "外套": False},
        "生活用品": {"牙刷牙膏": False, "常備藥": False, "塑膠袋": False, "折疊傘": False}
    }

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船", "✈️ 飛機"]

# 🌍 旅遊生存會話庫
SURVIVAL_PHRASES = {
    "日本": {
        "招呼": [("你好", "こんにちは (Konnichiwa)"), ("謝謝", "ありがとう (Arigatou)"), ("不好意思", "すみません (Sumimasen)")],
        "點餐": [("請給我這個", "これをください (Kore wo kudasai)"), ("買單", "お会計お願いします (Okaikei onegaishimasu)"), ("多少錢？", "いくらですか (Ikura desuka?)")],
        "交通": [("...在哪裡？", "…はどこですか？ (... wa doko desuka?)"), ("車站", "駅 (Eki)"), ("廁所", "トイレ (Toire)")],
        "購物": [("可以試穿嗎？", "試着してもいいですか (Shichaku shitemo ii desuka)"), ("有免稅嗎？", "免税できますか (Menzei dekimasuka)")],
        "緊急": [("救命", "助けて (Tasukete)"), ("我身體不舒服", "具合が悪いです (Guai ga warui desu)"), ("我不見了", "迷子になりました (Maigo ni narimashita)")]
    },
    "韓國": {
        "招呼": [("你好", "안녕하세요"), ("謝謝", "감사합니다"), ("不好意思", "저기요")],
        "點餐": [("請給我這個", "이거 주세요"), ("買單", "계산해 주세요"), ("好", "네")],
        "交通": [("...在哪裡？", "... 어디에요?"), ("車站", "역"), ("洗手間", "화장실")],
        "購物": [("多少錢？", "얼마예요?"), ("可以打折嗎？", "깎아 주세요")],
        "緊急": [("救命", "도와주세요"), ("痛", "아파요"), ("警察", "경찰")]
    },
    "泰國": {
        "招呼": [("你好", "Sawasdee khrup/kha"), ("謝謝", "Khop khun khrup/kha")],
        "點餐": [("我要這個", "Ao an nee"), ("多少錢", "Tao rai?"), ("不辣", "Mai pet")],
        "交通": [("去...", "Bai ..."), ("廁所", "Hong nam"), ("機場", "Sanam bin")],
        "購物": [("太貴了", "Paeng mak"), ("可以便宜點嗎", "Lot noi dai mai?")],
        "緊急": [("救命", "Chuay duay"), ("醫生", "Mor"), ("去醫
