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
    from folium import plugins
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

# --- AI 導遊對話 (串流版) ---
def ask_ai_guide_stream(prompt, context_data):
    """發送對話給 Gemini (串流模式)"""
    if not GEMINI_AVAILABLE:
        yield "系統提示：請先安裝 google-generativeai 套件。"
        return
    
    if "GEMINI_API_KEY" not in st.secrets:
        yield "系統提示：請先在 Secrets 設定 GEMINI_API_KEY。"
        return

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        system_prompt = f"""
        你是一位專業、幽默且貼心的私人旅遊導遊。
        
        【你的任務】：
        1. 根據使用者的問題，提供景點介紹、美食推薦、交通建議或行程規劃。
        2. 回答要簡潔有力，重點清晰，適合手機閱讀。
        3. 如果使用者問美食，請推薦具體的店名（如果知道的話）和必點菜色。
        
        【使用者目前的行程資料】：
        {json.dumps(context_data, ensure_ascii=False)}
        
        請根據上述行程資料來回答。
        """
        
        # 自動選擇模型
        target_model_name = 'models/gemini-1.5-flash'
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            priority = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
            for p in priority:
                if p in available_models:
                    target_model_name = p
                    break
        except: pass
        
        model = genai.GenerativeModel(target_model_name)
        
        # 組合對話歷史
        gemini_history = []
        if "chat_history" in st.session_state:
            for msg in st.session_state.chat_history:
                if msg["role"] == "assistant" and "你好！我是你的 AI 專業導遊" in msg["content"]:
                    continue
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})
        
        chat = model.start_chat(history=gemini_history)
        
        # 使用 stream=True
        response = chat.send_message(system_prompt + "\n\n使用者問題：" + prompt, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        yield f"AI 導遊連線錯誤：{e}"

# --- 收據分析 ---
def analyze_receipt_image(image_file):
    if not GEMINI_AVAILABLE:
        return [{"name": "飯糰 (模擬)", "price": 130}, {"name": "可樂 (模擬)", "price": 140}]
    
    if "GEMINI_API_KEY" not in st.secrets:
        return [{"name": "請設定 API Key", "price": 0}]

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        img = Image.open(image_file)
        
        prompt = """
        你是一個專業的旅遊記帳助手。請分析這張收據圖片，列出實際購買的商品明細。
        請嚴格遵守以下規則：
        1. 【翻譯】：將商品名稱翻譯成「繁體中文」，格式為：「原文 (中文翻譯)」。
        2. 【金額】：提取該項目的單價或總價（Integer）。
        3. 【排除】：絕對不要包含「小計」、「消費稅」、「合計」、「現計」、「釣錢(找零)」等統計欄位。
        4. 【格式】：直接回傳一個 JSON Array，不要有 Markdown 標記。
           範例：[{"name": "コカコーラ (可口可樂)", "price": 140}]
        """
        priority_models = ['models/gemini-2.0-flash', 'models/gemini-1.5-flash']
        target_model_name = 'models/gemini-1.5-flash'
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            for candidate in priority_models:
                if candidate in available_models:
                    target_model_name = candidate
                    break
        except: pass
        
        model = genai.GenerativeModel(target_model_name)
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "")
        
        data = json.loads(text)
        if isinstance(data, dict): return [data]
        return data

    except Exception as e:
        return [{"name": f"分析失敗: {e}", "price": 0}]

# --- 地理編碼 ---
@st.cache_data
def get_lat_lon(location_name):
    if not MAP_AVAILABLE: return None
    try:
        geolocator = Nominatim(user_agent="trip_planner_v17_stream")
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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "你好！我是你的 AI 專業導遊。我可以幫你規劃行程、介紹景點、推薦美食，或提醒你旅遊注意事項。"}
    ]

# 用來觸發快速按鈕的 AI 請求
if "pending_ai_query" not in st.session_state:
    st.session_state.pending_ai_query = None

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
        "緊急": [("救命", "Chuay duay"), ("醫生", "Mor"), ("去醫院", "Bai rong paya ban")]
    }
}

# -------------------------------------
# 4. CSS 樣式
# -------------------------------------
c_bg = current_theme['bg']
c_text = current_theme['text']
c_card = current_theme['card']
c_primary = current_theme['primary']
c_sub = current_theme['sub']
c_sec = current_theme['secondary']

main_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&family=Inter:wght@400;600&display=swap');

.stApp {{ background-color: {c_bg} !important; color: {c_text} !important; font-family: 'Inter', 'Noto Serif JP', sans-serif !important; }}
[data-testid="stSidebarCollapsedControl"], footer {{ display: none !important; }}
header[data-testid="stHeader"] {{ height: 0 !important; background: transparent !important; }}

/* Apple Style Cards */
.apple-card {{
    background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px);
    border-radius: 18px; padding: 18px; margin-bottom: 0px;
    border: 1px solid rgba(255, 255, 255, 0.6); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
}}
.apple-time {{ font-weight: 700; font-size: 1.1rem; color: {c_text}; }}
.apple-loc {{ font-size: 0.9rem; color: {c_sub}; display:flex; align-items:center; gap:5px; margin-top:5px; }}

/* Weather Widget */
.apple-weather-widget {{
    background: linear-gradient(135deg, {c_primary} 0%, {c_text} 150%);
    color: white; padding: 15px 20px; border-radius: 20px;
    margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    display: flex; align-items: center; justify-content: space-between;
}}

/* Transport Card */
.trans-card {{
    background: #FFFFFF; border-radius: 12px; padding: 10px 15px;
    margin: 10px 0 10px 50px; border: 1px solid #E0E0E0;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}}
.trans-tag {{
    font-size: 0.75rem; padding: 3px 8px; border-radius: 6px;
    background: #F0F4F8; color: #486581; font-weight: bold;
}}

/* Day Segmented Control */
div[data-testid="stRadio"] > div {{
    background-color: {c_sec} !important; padding: 4px !important; border-radius: 12px !important; 
    gap: 0px !important; border: none !important; overflow-x: auto; flex-wrap: nowrap;
}}
div[data-testid="stRadio"] label {{
    background-color: transparent !important; border: none !important;
    flex: 1 !important; text-align: center !important; justify-content: center !important;
    border-radius: 9px !important; height: auto !important; min-width: 50px !important;
}}
div[data-testid="stRadio"] label[data-checked="true"] {{
    background-color: {c_card} !important; color: {c_text} !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important; font-weight: bold !important;
}}

/* Info Cards */
.info-card {{
    background-color: {c_card}; border-radius: 12px; padding: 20px; margin-bottom: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #F0F0F0;
}}
.info-tag {{ background: {c_bg}; color: {c_sub}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}

/* UI Tweaks */
button[data-baseweb="tab"] {{ border-radius: 20px !important; margin-right:5px !important; }}
div[data-baseweb="input"], div[data-baseweb="base-input"] {{ border: none !important; border-bottom: 1px solid {c_sec} !important; background: transparent !important; }}
input {{ color: {c_text} !important; }}
</style>
"""
st.markdown(main_css, unsafe_allow_html=True)

# -------------------------------------
# 5. 主畫面
# -------------------------------------
st.markdown(f'<div style="font-size:2.2rem; font-weight:900; text-align:center; margin-bottom:5px; color:{c_text};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown(f'<div style="text-align:center; color:{c_sub}; font-size:0.9rem; margin-bottom:20px;">{st.session_state.start_date.strftime("%Y/%m/%d")} 出發</div>', unsafe_allow_html=True)

with st.expander("⚙️ 設定"):
    st.session_state.trip_title = st.text_input("標題", value=st.session_state.trip_title)
    theme_name = st.selectbox("主題", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.selected_theme_name))
    if theme_name != st.session_state.selected_theme_name:
        st.session_state.selected_theme_name = theme_name
        st.rerun()
    c1, c2 = st.columns(2)
    st.session_state.start_date = c1.date_input("日期", value=st.session_state.start_date)
    st.session_state.trip_days_count = c2.number_input("天數", 1, 30, st.session_state.trip_days_count)
    st.session_state.target_country = st.selectbox("地區", ["日本", "韓國", "泰國", "台灣"])
    st.session_state.exchange_rate = st.number_input("匯率 (外幣 -> 台幣)", value=st.session_state.exchange_rate, step=0.01)
    uf = st.file_uploader("匯入 Excel", type=["xlsx"])
    if uf and st.button("匯入"): process_excel_upload(uf)

# Init Days
for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

# Tabs (新增 Tab 7: AI 導遊)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📅 行程", "🗺️ 地圖", "✨ 願望", "🎒 清單", "ℹ️ 資訊", "🧰 工具", "🤖 AI 導遊"])

# ==========================================
# 1. 行程規劃
# ==========================================
with tab1:
    selected_day_num = st.radio("DaySelect", list(range(1, st.session_state.trip_days_count + 1)), 
                                index=0, horizontal=True, label_visibility="collapsed", 
                                format_func=lambda x: f"Day {x}")
    
    current_date = st.session_state.start_date + timedelta(days=selected_day_num - 1)
    current_items = st.session_state.trip_data[selected_day_num]
    current_items.sort(key=lambda x: x['time'])
    
    # 預算儀表板
    all_cost = sum([item.get('cost', 0) for item in current_items])
    all_actual = sum([sum(x['price'] for x in item.get('expenses', [])) for item in current_items])
    
    c_bud1, c_bud2 = st.columns(2)
    c_bud1.metric("今日預算", f"¥{all_cost:,}")
    c_bud2.metric("實際支出", f"¥{all_actual:,}", delta=f"{all_cost - all_actual:,}" if all_actual > 0 else None)
    if all_cost > 0 and all_actual > 0:
        st.progress(min(all_actual / all_cost, 1.0), text=f"支出進度 {int(min(all_actual / all_cost, 1.0)*100)}%")

    st.markdown("---")

    # 天氣
    first_loc = current_items[0]['loc'] if current_items and current_items[0]['loc'] else (st.session_state.target_country if st.session_state.target_country != "日本" else "京都")
    weather = WeatherService.get_forecast(first_loc, current_date)
    
    # HTML 壓縮單行
    weather_html = f"""<div class="apple-weather-widget"><div style="display:flex; align-items:center; gap:15px;"><div style="font-size:2.5rem;">{weather['icon']}</div><div><div style="font-size:2rem; font-weight:700; line-height:1;">{weather['high']}°</div><div style="font-size:0.9rem; opacity:0.9;">L:{weather['low']}°</div></div></div><div style="text-align:right;"><div style="font-weight:700;">{current_date.strftime('%m/%d %a')}</div><div style="font-size:0.9rem; opacity:0.9;">📍 {first_loc}</div><div style="font-size:0.8rem; opacity:0.8; margin-top:2px;">{weather['desc']}</div></div></div>"""
    st.markdown(weather_html, unsafe_allow_html=True)

    is_edit_mode = st.toggle("編輯模式 (含收據掃描)")
    
    if is_edit_mode and st.button("➕ 新增行程", use_container_width=True):
        st.session_state.trip_data[selected_day_num].append({"id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": "", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30})
        st.rerun()

    if not current_items:
        st.info("🍵 點擊「編輯模式」開始安排今日行程")

    for index, item in enumerate(current_items):
        map_link = get_single_map_link(item['loc'])
        map_btn = f'<a href="{map_link}" target="_blank" style="text-decoration:none; margin-left:8px; font-size:0.8rem; background:{c_sec}; color:{c_text}; padding:2px 8px; border-radius:10px; opacity:0.8;">🗺️</a>' if item['loc'] else ""
        
        cost_display = ""
        total_exp = sum(x['price'] for x in item.get('expenses', []))
        final_cost = total_exp if total_exp > 0 else item.get('cost', 0)
        if final_cost > 0:
            cost_display = f'<div style="background:{c_primary}; color:white; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:bold; white-space:nowrap;">¥{final_cost:,}</div>'

        clean_note = item["note"].replace('\n', '<br>')
        note_div = f'<div style="font-size:0.85rem; color:{c_sub}; background:{c_bg}; padding:8px; border-radius:8px; margin-top:8px; line-height:1.4;">📝 {clean_note}</div>' if item['note'] and not is_edit_mode else ""
        
        # 行程卡片 HTML
        card_html = f"""<div style="display:flex; gap:15px; margin-bottom:0px;"><div style="display:flex; flex-direction:column; align-items:center; width:50px;"><div style="font-weight:700; color:{c_text}; font-size:1.1rem;">{item['time']}</div><div style="flex-grow:1; width:2px; background:{c_sec}; margin:5px 0; opacity:0.3; border-radius:2px;"></div></div><div style="flex-grow:1;"><div class="apple-card" style="margin-bottom:0px;"><div style="display:flex; justify-content:space-between; align-items:flex-start;"><div class="apple-title" style="margin-top:0;">{item['title']}</div>{cost_display}</div><div class="apple-loc">📍 {item['loc'] or '未設定'} {map_btn}</div>{note_div}</div></div></div>"""
        st.markdown(card_html, unsafe_allow_html=True)

        # 明細折疊區 (可隱藏)
        if item.get('expenses'):
            with st.expander(f"🧾 查看消費明細 (合計 ¥{final_cost:,})", expanded=False):
                for exp in item['expenses']:
                    st.markdown(f"**{exp['name']}** : ¥{exp['price']:,}")

        if is_edit_mode:
            with st.expander("💰 記帳與收據掃描 (點擊展開)", expanded=False):
                c1, c2 = st.columns([2, 1])
                item['title'] = c1.text_input("名稱", item['title'], key=f"t_{item['id']}")
                item['time'] = c2.time_input("時間", datetime.strptime(item['time'], "%H:%M").time(), key=f"tm_{item['id']}").strftime("%H:%M")
                item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                item['cost'] = st.number_input("預算 (¥)", value=item['cost'], step=100, key=f"c_{item['id']}")
                item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                
                st.markdown("---")
                
                input_method = st.radio("輸入方式", ["📸 拍照", "📂 上傳"], horizontal=True, key=f"in_method_{item['id']}")
                uploaded_receipt = None
                
                if input_method == "📸 拍照":
                    if st.toggle("🔴 啟動相機", key=f"toggle_cam_{item['id']}"):
                        uploaded_receipt = st.camera_input("拍照", key=f"cam_{item['id']}", label_visibility="collapsed")
                else:
                    uploaded_receipt = st.file_uploader("上傳", type=["jpg","png"], key=f"upl_{item['id']}", label_visibility="collapsed")

                scan_flag_key = f"scan_done_{item['id']}"
                
                if uploaded_receipt and not st.session_state.get(scan_flag_key, False):
                    with st.spinner("正在分析收據..."):
                        results = analyze_receipt_image(uploaded_receipt)
                    
                    if isinstance(results, list):
                        count = 0
                        total_p = 0
                        for res in results:
                            n = res.get('name', '未知商品')
                            p = res.get('price', 0)
                            if p > 0:
                                item['expenses'].append({'name': n, 'price': p})
                                total_p += p
                                count += 1
                        
                        if count > 0:
                            item['cost'] = sum(x['price'] for x in item['expenses'])
                            st.success(f"已自動加入 {count} 筆明細")
                            st.session_state[scan_flag_key] = True
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("未能辨識出有效金額")
                    else:
                        st.error("分析格式錯誤")
                
                if not uploaded_receipt and st.session_state.get(scan_flag_key, False):
                    st.session_state[scan_flag_key] = False

                cx1, cx2, cx3 = st.columns([2, 1, 1])
                cx1.text_input("項目", key=f"new_exp_n_{item['id']}", placeholder="項目", label_visibility="collapsed")
                cx2.number_input("金額", min_value=0, key=f"new_exp_p_{item['id']}", label_visibility="collapsed")
                cx3.button("➕", key=f"add_{item['id']}", on_click=add_expense_callback, args=(item['id'], selected_day_num))
                
                if item.get('expenses'):
                    st.write("已記錄項目：")
                    for i_ex, ex in enumerate(item['expenses']):
                        c_d1, c_d2 = st.columns([3,1])
                        c_d1.text(f"{ex['name']} ¥{ex['price']}")
                        if c_d2.button("刪", key=f"del_exp_{item['id']}_{i_ex}"):
                            item['expenses'].pop(i_ex)
                            st.rerun()

                if st.button("🗑️ 刪除行程", key=f"del_{item['id']}"):
                    st.session_state.trip_data[selected_day_num].pop(index)
                    st.rerun()
        
        if index < len(current_items) - 1:
            next_item = current_items[index+1]
            t_mode = item.get('trans_mode', '📍 移動')
            t_min = item.get('trans_min', 30)
            nav_link = generate_google_nav_link(item['loc'], next_item['loc'])
            
            if is_edit_mode:
                 ct1, ct2 = st.columns([1,1])
                 item['trans_mode'] = ct1.selectbox("交通", TRANSPORT_OPTIONS, key=f"trm_{item['id']}")
                 item['trans_min'] = ct2.number_input("分", value=t_min, step=5, key=f"trmin_{item['id']}")
            else:
                 trans_html = f"""<div style="display:flex; gap:15px;"><div style="display:flex; flex-direction:column; align-items:center; width:50px;"><div style="flex-grow:1; width:2px; border-left:2px dashed {c_sec}; margin:0; opacity:0.6;"></div></div><div style="flex-grow:1; padding:5px 0;"><div class="trans-card"><div style="display:flex; flex-direction:column;"><div style="font-size:0.7rem; color:#888; margin-bottom:2px;">推薦路線 (RECOMMENDED)</div><div style="display:flex; align-items:center; gap:8px;"><div style="font-weight:bold; font-size:0.9rem;">{t_mode}</div><div class="trans-tag">最快速</div></div></div><div style="text-align:right;"><div style="font-weight:bold; font-size:0.9rem;">{t_min} min</div><a href="{nav_link}" target="_blank" style="text-decoration:none; font-size:0.75rem; color:#007AFF;">➤ 導航</a></div></div></div></div>"""
                 st.markdown(trans_html, unsafe_allow_html=True)

# ==========================================
# 2. 地圖軌跡 (回歸路線圖)
# ==========================================
with tab2:
    st.subheader(f"🗺️ Day {selected_day_num} 路線圖")
    
    map_items = sorted(st.session_state.trip_data[selected_day_num], key=lambda x: x['time'])
    route_url = generate_google_map_route(map_items)
    st.markdown(f"<div style='text-align:center; margin-bottom:15px;'><a href='{route_url}' target='_blank' style='background:{c_primary}; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold; box-shadow:0 4px 10px rgba(0,0,0,0.2);'>🚗 Google Maps 完整導航</a></div>", unsafe_allow_html=True)

    if MAP_AVAILABLE:
        valid_map_items = [it for it in map_items if it['loc']]
        if valid_map_items:
            start_coords = get_lat_lon(valid_map_items[0]['loc'])
            if not start_coords: start_coords = [35.6895, 139.6917]
            
            m = folium.Map(location=start_coords, zoom_start=13)
            route_coords = []
            
            for idx, item in enumerate(valid_map_items):
                coords = get_lat_lon(item['loc'])
                if coords:
                    route_coords.append(coords)
                    plugins.BeautifyIcon(number=idx + 1, border_color="#007AFF", text_color="#007AFF", icon_shape="marker").add_to(folium.Marker(coords, popup=item['title']).add_to(m))
            
            if len(route_coords) > 1:
                folium.PolyLine(route_coords, color="#007AFF", weight=5, opacity=0.8, tooltip="行程路線").add_to(m)
            
            st_folium(m, width="100%", height=400)
        else:
            st.info("本行程尚無有效地點，無法繪製地圖。")
    else:
        st.warning("請安裝 folium 與 streamlit-folium 套件以顯示互動地圖。")

# ==========================================
# 3. 願望清單
# ==========================================
with tab3:
    st.subheader("✨ 願望清單")
    with st.expander("➕ 新增願望", expanded=False):
        w_title = st.text_input("名稱")
        w_loc = st.text_input("地點")
        w_note = st.text_input("備註")
        if st.button("加入") and w_title:
            st.session_state.wishlist.append({"id": int(time.time()), "title": w_title, "loc": w_loc, "note": w_note})
            st.rerun()

    for i, wish in enumerate(st.session_state.wishlist):
        with st.container():
            wish_html = f"""<div class="apple-card" style="padding:15px; margin-bottom:10px; border-left:4px solid {c_primary};"><div style="font-weight:bold; font-size:1.1rem;">{wish['title']}</div><div style="font-size:0.9rem; color:{c_sub};">📍 {wish['loc']}｜📝 {wish['note']}</div></div>"""
            st.markdown(wish_html, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([2, 1, 1])
            target_day = c1.selectbox("移至", list(range(1, st.session_state.trip_days_count + 1)), key=f"wd_{wish['id']}")
            if c2.button("排程", key=f"wm_{wish['id']}"):
                new_item = {"id": int(time.time()), "time": "09:00", "title": wish['title'], "loc": wish['loc'], "cost": 0, "cat": "spot", "note": wish['note'], "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
                st.session_state.trip_data[target_day].append(new_item)
                st.session_state.wishlist.pop(i)
                st.toast(f"已排入 Day {target_day}")
                time.sleep(1)
                st.rerun()
            if c3.button("刪", key=f"wdl_{wish['id']}"):
                st.session_state.wishlist.pop(i)
                st.rerun()

# ==========================================
# 4. 準備清單
# ==========================================
with tab4:
    recs = get_packing_recommendations(st.session_state.trip_data, st.session_state.start_date)
    st.info(f"**🌤️ 智能穿搭推薦**\n建議攜帶：" + "、".join(recs))
    c_list_head, c_list_edit = st.columns([3, 1])
    c_list_head.subheader("🎒 準備清單")
    edit_list_mode = c_list_edit.toggle("編輯")
    for category, items in st.session_state.checklist.items():
        st.markdown(f"**{category}**")
        cols = st.columns(2)
        keys_del = []
        for i, (item, checked) in enumerate(items.items()):
            col = cols[i % 2]
            if edit_list_mode:
                c1, c2 = col.columns([4,1])
                c1.text(item)
                if c2.button("x", key=f"d_{category}_{item}"): keys_del.append(item)
            else:
                st.session_state.checklist[category][item] = col.checkbox(item, value=checked, key=f"c_{category}_{item}")
        if keys_del:
            for k in keys_del: del st.session_state.checklist[category][k]
            st.rerun()
        if edit_list_mode:
            new_i = st.text_input(f"加到 {category}", key=f"n_{category}")
            if new_i and st.button("➕", key=f"btn_{category}"):
                st.session_state.checklist[category][new_i] = False
                st.rerun()

# ==========================================
# 5. 重要資訊
# ==========================================
with tab5:
    col_info_1, col_info_2 = st.columns([3, 1])
    col_info_1.subheader("✈️ 航班")
    edit_info_mode = col_info_2.toggle("✏️ 編輯資訊")
    flights = st.session_state.flight_info
    for f_key, f_label in [("outbound", "去程"), ("inbound", "回程")]:
        f_data = flights[f_key]
        if edit_info_mode:
            with st.container(border=True):
                st.caption(f"編輯 {f_label}")
                c1, c2 = st.columns(2)
                f_data["date"] = c1.text_input("日期", f_data["date"], key=f"fd_{f_key}")
                f_data["code"] = c2.text_input("航班", f_data["code"], key=f"fc_{f_key}")
                f_data["dep"] = c1.text_input("起飛", f_data["dep"], key=f"ft1_{f_key}")
                f_data["arr"] = c2.text_input("抵達", f_data["arr"], key=f"ft2_{f_key}")
                f_data["dep_loc"] = c1.text_input("起飛地", f_data["dep_loc"], key=f"fl1_{f_key}")
                f_data["arr_loc"] = c2.text_input("抵達地", f_data["arr_loc"], key=f"fl2_{f_key}")
        
        flight_html = f"""<div class="info-card"><div class="info-header"><span>📅 {f_data['date']}</span> <span>✈️ {f_data['code']}</span></div><div class="info-time">{f_data['dep']} -> {f_data['arr']}</div><div class="info-loc"><span>📍 {f_data['dep_loc']}</span> <span style="margin:0 5px;">✈</span> <span>{f_data['arr_loc']}</span></div><div style="text-align:right; margin-top:5px;"><span class="info-tag">{f_label}</span></div></div>"""
        st.markdown(flight_html, unsafe_allow_html=True)

    st.divider()
    st.subheader("🏨 住宿")
    if edit_info_mode:
        if st.button("➕ 新增住宿"):
            st.session_state.hotel_info.append({"id": int(time.time()), "name": "新飯店", "range": "D1-D2", "date": "", "addr": "", "link": ""})
            st.rerun()
    for i, hotel in enumerate(st.session_state.hotel_info):
        if edit_info_mode:
            with st.expander(f"編輯: {hotel['name']}", expanded=True):
                hotel['name'] = st.text_input("飯店名稱", hotel['name'], key=f"hn_{hotel['id']}")
                hotel['range'] = st.text_input("天數", hotel['range'], key=f"hr_{hotel['id']}")
                hotel['date'] = st.text_input("日期範圍", hotel['date'], key=f"hd_{hotel['id']}")
                hotel['addr'] = st.text_input("地址", hotel['addr'], key=f"ha_{hotel['id']}")
                hotel['link'] = st.text_input("連結", hotel['link'], key=f"hl_{hotel['id']}")
                if st.button("🗑️ 刪除", key=f"del_h_{hotel['id']}"):
                    st.session_state.hotel_info.pop(i)
                    st.rerun()
        
        map_url = get_single_map_link(hotel['link']) if hotel['link'] else get_single_map_link(hotel['name'])
        hotel_card_html = f"""<div class="info-card" style="border-left: 5px solid {c_primary};"><div class="info-header"><span class="info-tag" style="background:{c_primary}; color:white;">{hotel['range']}</span><span>{hotel['date']}</span></div><div style="font-size:1.3rem; font-weight:900; color:{c_text}; margin: 10px 0;">{hotel['name']}</div><div class="info-loc" style="margin-bottom:10px;">📍 {hotel['addr']}</div><a href="{map_url}" target="_blank" style="text-decoration:none; color:{c_primary}; font-size:0.9rem; font-weight:bold; border:1px solid {c_primary}; padding:4px 12px; border-radius:20px;">🗺️ 地圖</a></div>"""
        st.markdown(hotel_card_html, unsafe_allow_html=True)

# ==========================================
# 6. 工具
# ==========================================
with tab6:
    st.header("🧰 實用工具")
    
    st.subheader("☁️ 雲端同步")
    c1, c2 = st.columns(2)
    if c1.button("☁️ 上傳"):
        if CLOUD_AVAILABLE:
            data = {"trip": st.session_state.trip_data, "wish": st.session_state.wishlist, "check": st.session_state.checklist}
            res = save_to_cloud(json.dumps(data, default=str))
            st.toast(res[1] if res[0] else f"錯誤: {res[1]}")
        else: st.error("缺少雲端套件")
    if c2.button("📥 下載"):
        if CLOUD_AVAILABLE:
            raw = load_from_cloud()
            if raw:
                d = json.loads(raw)
                if "trip" in d: st.session_state.trip_data = {int(k):v for k,v in d['trip'].items()}
                st.toast("成功")
                time.sleep(1)
                st.rerun()
        else: st.error("缺少雲端套件")

    st.divider()
    
    st.subheader("💴 匯率")
    amt = st.number_input("外幣", step=100)
    st.metric("台幣", int(amt * st.session_state.exchange_rate))
    
    st.divider()
    
    st.subheader("🛍️ 購物")
    edited_df = st.data_editor(st.session_state.shopping_list, num_rows="dynamic", key="shop_edit")
    if not edited_df.equals(st.session_state.shopping_list):
        st.session_state.shopping_list = edited_df
        st.rerun()
    
    st.divider()
    
    st.subheader("🆘 緊急")
    target_country_sos = st.session_state.target_country
    if target_country_sos in SURVIVAL_PHRASES: 
        sos_map = {
            "日本": {"迷路": "迷子になりました", "過敏": "アレルギーがあります", "醫院": "病院に連れて行って"},
            "韓國": {"迷路": "길을 잃었어요", "過敏": "알레르기가 있어요", "醫院": "병원으로 가주세요"},
            "泰國": {"迷路": "Long tang", "過敏": "Pae a-han", "醫院": "Bai rong paya ban"}
        }
        if target_country_sos in sos_map:
            s_type = st.selectbox("狀況", list(sos_map[target_country_sos].keys()))
            s_txt = sos_map[target_country_sos][s_type]
            st.markdown(f"<div style='background:#D32F2F; color:white; padding:20px; border-radius:10px; text-align:center; font-size:1.5rem;'>{s_txt}</div>", unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("🗣️ 會話")
    if target_country_sos in SURVIVAL_PHRASES:
        phrases = SURVIVAL_PHRASES[target_country_sos]
        cat = st.selectbox("情境", list(phrases.keys()))
        for p in phrases[cat]:
            st.markdown(f"<div class='apple-card' style='padding:10px; margin-bottom:5px;'>{p[0]}<br><b>{p[1]}</b></div>", unsafe_allow_html=True)

# ==========================================
# 7. AI 導遊
# ==========================================
with tab7:
    st.header("🤖 AI 隨身導遊")
    
    # 初始化觸發器
    if "trigger_ai" not in st.session_state:
        st.session_state.trigger_ai = False
    if "trigger_query" not in st.session_state:
        st.session_state.trigger_query = ""

    col_head_1, col_head_2 = st.columns([4, 1])
    if col_head_2.button("🗑️ 清除"):
        st.session_state.chat_history = [{"role": "assistant", "content": "你好！我是你的 AI 專業導遊。"}]
        st.rerun()

    # 顯示歷史訊息
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # 處理來自快速按鈕的觸發
    if st.session_state.trigger_ai:
        prompt = st.session_state.trigger_query
        st.session_state.trigger_ai = False # 重置觸發器
        st.session_state.trigger_query = ""
        
        # 顯示使用者訊息
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # 生成回應
        with st.chat_message("assistant"):
            context_data = {
                "target_country": st.session_state.target_country,
                "current_trip_data": st.session_state.trip_data,
                "current_date": datetime.now().strftime("%Y-%m-%d")
            }
            response_stream = ask_ai_guide_stream(prompt, context_data)
            full_response = st.write_stream(response_stream)
            
        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
        st.rerun()

    # 一般輸入框
    if prompt := st.chat_input("問我行程、美食或交通問題..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.chat_message("assistant"):
            context_data = {
                "target_country": st.session_state.target_country,
                "current_trip_data": st.session_state.trip_data,
                "current_date": datetime.now().strftime("%Y-%m-%d")
            }
            response_stream = ask_ai_guide_stream(prompt, context_data)
            full_response = st.write_stream(response_stream)
            
        st.session_state.chat_history.append({"role": "assistant", "content": full_response})

    st.markdown("---")
    st.caption("快速提問：")
    col_q1, col_q2, col_q3 = st.columns(3)
    
    # 快速按鈕邏輯修改：不直接 append，而是設定 trigger
    if col_q1.button("📅 檢視行程"):
        st.session_state.trigger_query = "請幫我檢查目前的行程安排是否順暢，有沒有建議修改的地方？"
        st.session_state.trigger_ai = True
        st.rerun()
        
    if col_q2.button("🍜 美食推薦"):
        st.session_state.trigger_query = "根據我目前的行程地點，推薦一些附近必吃的美食。"
        st.session_state.trigger_ai = True
        st.rerun()
        
    if col_q3.button("⚠️ 注意事項"):
        st.session_state.trigger_query = f"去{st.session_state.target_country}旅遊有什麼需要特別注意的事項或禮儀？"
        st.session_state.trigger_ai = True
        st.rerun()
