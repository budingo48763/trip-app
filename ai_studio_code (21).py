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

# --- 收據分析 ---
def analyze_receipt_image(image_file):
    if not GEMINI_AVAILABLE:
        # 模擬多筆資料
        return [{"name": "模擬-商品A", "price": 1200}, {"name": "模擬-商品B", "price": 800}]
    
    if "GEMINI_API_KEY" not in st.secrets:
        return [{"name": "請設定 API Key", "price": 0}]

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        img = Image.open(image_file)
        
        prompt = """
        你是一個旅遊記帳助手。請分析這張收據。
        1. 提取所有商品名稱與金額。
        2. 翻譯成繁體中文。
        3. 排除小計、稅金、找零。
        4. 回傳 JSON Array: [{"name": "商品", "price": 100}, ...]
        5. price 為整數。不要 Markdown。
        """

        # 嘗試多種模型
        target_model = 'models/gemini-1.5-flash'
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini-2.0' in m.name: target_model = m.name; break
        except: pass

        model = genai.GenerativeModel(target_model)
        response = model.generate_content([prompt, img])
        text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        return data if isinstance(data, list) else [data]

    except Exception:
        return [{"name": "分析失敗", "price": 0}]

# --- 地理編碼 ---
@st.cache_data
def get_lat_lon(location_name):
    if not MAP_AVAILABLE: return None
    try:
        geolocator = Nominatim(user_agent="trip_planner_final_fix_v2")
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
        return gspread.authorize(creds)
    except: return None

def save_to_cloud(json_str):
    client = get_cloud_connection()
    if client:
        try:
            client.open("TripPlanDB").sheet1.update_cell(1, 1, json_str)
            return True, "成功"
        except Exception as e: return False, str(e)
    return False, "失敗"

def load_from_cloud():
    client = get_cloud_connection()
    if client:
        try: return client.open("TripPlanDB").sheet1.cell(1, 1).value
        except: return None
    return None

class WeatherService:
    ICONS = {"Sunny": "☀️", "Cloudy": "☁️", "Rainy": "🌧️", "Snowy": "❄️"}
    @staticmethod
    def get_forecast(loc, date):
        random.seed(f"{loc}{date}")
        base = 20 if date.month not in [12,1,2] else 5
        cond = random.choice(["Sunny", "Cloudy", "Rainy"])
        desc = {"Sunny":"晴","Cloudy":"陰","Rainy":"雨","Snowy":"雪"}
        return {"high":base+5, "low":base-3, "icon":WeatherService.ICONS[cond], "desc":desc[cond], "raw":cond}

def get_packing(trip, start):
    recs = set()
    has_rain = False
    for day, items in trip.items():
        loc = items[0]['loc'] if items else "City"
        w = WeatherService.get_forecast(loc, start + timedelta(days=day-1))
        if w['raw'] in ["Rainy","Snowy"]: has_rain = True
    if has_rain: recs.add("☔ 雨具")
    recs.add("🧢 防曬")
    return list(recs)

def add_expense_callback(iid, d):
    n = st.session_state.get(f"n_{iid}", "")
    p = st.session_state.get(f"p_{iid}", 0)
    if n and p > 0:
        item = next((x for x in st.session_state.trip_data[d] if x['id'] == iid), None)
        if item:
            if "expenses" not in item: item["expenses"] = []
            item['expenses'].append({"name": n, "price": p})
            item['cost'] = sum(x['price'] for x in item['expenses'])
            st.session_state[f"n_{iid}"] = ""
            st.session_state[f"p_{iid}"] = 0

def get_map_link(loc):
    return loc if loc.startswith("http") else f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(loc)}"

def get_nav_link(o, d):
    return f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(o)}&destination={urllib.parse.quote(d)}&travelmode=transit"

def get_route_link(items):
    valid = [urllib.parse.quote(i['loc']) for i in items if i.get('loc')]
    return f"https://www.google.com/maps/dir/{'/'.join(valid)}" if valid else "#"

def process_excel(file):
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
if "wishlist" not in st.session_state: st.session_state.wishlist = [{"id":999, "title":"HARBS", "loc":"京都", "note":"蛋糕"}]
if "shopping_list" not in st.session_state: st.session_state.shopping_list = pd.DataFrame(columns=["對象","商品","預算","已買"])

cur = THEMES[st.session_state.selected_theme_name]

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id": 101, "time": "10:00", "title": "抵達", "loc": "關西機場", "cost": 0, "note": "入境", "expenses": [], "trans_mode": "🚆", "trans_min": 45}],
        2: [{"id": 201, "time": "09:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "note": "", "expenses": [], "trans_mode": "🚶", "trans_min": 20}],
        3: [], 4: [], 5: []
    }

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {"out":{"date":"1/17","code":"JX821","dep":"10:00","arr":"13:30","d":"TPE","a":"KIX"}, "in":{"date":"1/22","code":"JX822","dep":"15:00","arr":"17:10","d":"KIX","a":"TPE"}}

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [{"id":1, "name":"KOKO HOTEL", "range":"D1-D3", "date":"1/17-1/19", "addr":"京都", "link":""}]

if "checklist" not in st.session_state:
    st.session_state.checklist = {"證件":{"護照":False}, "電子":{"網卡":False}, "衣物":{"外套":False}}

PHRASES = {
    "日本": {"招呼":[("你好","こんにちは"),("謝謝","ありがとう")], "購物":[("免稅","免税OK?"),("多少錢","いくら?")]},
    "韓國": {"招呼":[("你好","안녕하세요"),("謝謝","감사합니다")], "購物":[("多少錢","얼마예요"),("打折","깎아 주세요")]},
    "泰國": {"招呼":[("你好","Sawasdee"),("謝謝","Khop khun")], "購物":[("多少錢","Tao rai"),("太貴","Paeng mak")]}
}
if st.session_state.target_country not in PHRASES: PHRASES[st.session_state.target_country] = {"通用": [("你好","Hello")]}

# -------------------------------------
# 4. CSS (使用取代法，最安全)
# -------------------------------------
css_template = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=Inter:wght@400;600&display=swap');
.stApp { background-color: __BG__ !important; color: __TXT__ !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebarCollapsedControl"], footer { display: none !important; }
header[data-testid="stHeader"] { height: 0 !important; background: transparent !important; }

/* Apple Card */
.apple-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 0px;
    border: 1px solid rgba(255,255,255,0.6);
    box-shadow: 0 4px 20px rgba(0,0,0,0.04);
}
.apple-time { font-weight: 700; font-size: 1.1rem; color: __TXT__; }
.apple-loc { font-size: 0.9rem; color: __SUB__; display:flex; align-items:center; gap:5px; margin-top:5px; }

/* Weather Widget */
.apple-weather {
    background: linear-gradient(135deg, __PRI__ 0%, __TXT__ 150%);
    color: white;
    padding: 18px 22px;
    border-radius: 22px;
    margin-bottom: 25px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

/* Transport Card (Google Maps Style) */
.trans-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 10px 15px;
    margin: 8px 0 8px 50px;
    border: 1px solid #E5E5EA;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}
.trans-tag {
    font-size: 0.7rem; padding: 3px 8px; border-radius: 6px;
    background: #F2F2F7; color: #636366; font-weight: 600; margin-left: 8px;
}

/* Elements */
div[data-testid="stRadio"] > div { background-color: __SEC__; padding: 4px; border-radius: 12px; overflow-x: auto; flex-wrap: nowrap; }
div[data-testid="stRadio"] label { background: transparent; border: none; flex: 1; text-align: center; border-radius: 9px; }
div[data-testid="stRadio"] label[data-checked="true"] { background-color: __CARD__; color: __TXT__; box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-weight: bold; }
input { color: __TXT__ !important; }
</style>
"""
# 替換 CSS 變數
for k, v in [("__BG__", cur['bg']), ("__TXT__", cur['text']), ("__PRI__", cur['primary']), ("__SEC__", cur['secondary']), ("__CARD__", cur['card']), ("__SUB__", cur['sub'])]:
    css_template = css_template.replace(k, v)
st.markdown(css_template, unsafe_allow_html=True)

# -------------------------------------
# 5. UI
# -------------------------------------
st.markdown(f'<div style="font-size:2.2rem;font-weight:900;text-align:center;color:{cur["text"]};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown(f'<div style="text-align:center;color:{cur["sub"]};font-size:0.9rem;margin-bottom:20px;">{st.session_state.start_date.strftime("%Y/%m/%d")} 出發</div>', unsafe_allow_html=True)

with st.expander("⚙️ 設定"):
    st.session_state.trip_title = st.text_input("標題", st.session_state.trip_title)
    tn = st.selectbox("主題", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.selected_theme_name))
    if tn != st.session_state.selected_theme_name:
        st.session_state.selected_theme_name = tn
        st.rerun()
    c1, c2 = st.columns(2)
    st.session_state.start_date = c1.date_input("日期", st.session_state.start_date)
    st.session_state.trip_days_count = c2.number_input("天數", 1, 30, st.session_state.trip_days_count)
    st.session_state.target_country = st.selectbox("地區", ["日本", "韓國", "泰國", "台灣"])
    st.session_state.exchange_rate = st.number_input("匯率", value=st.session_state.exchange_rate, step=0.01)
    uf = st.file_uploader("匯入 Excel", type=["xlsx"])
    if uf and st.button("匯入"): process_excel(uf)

for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

t1, t2, t3, t4, t5, t6 = st.tabs(["📅 行程", "🗺️ 地圖", "✨ 願望", "🎒 清單", "ℹ️ 資訊", "🧰 工具"])

# --- Tab 1: 行程 ---
with t1:
    day = st.radio("Day", list(range(1, st.session_state.trip_days_count + 1)), horizontal=True, label_visibility="collapsed", format_func=lambda x: f"D{x}")
    curr_d = st.session_state.start_date + timedelta(days=day-1)
    items = st.session_state.trip_data[day]
    items.sort(key=lambda x: x['time'])
    
    # 預算
    tc = sum([it['cost'] for it in items])
    ta = sum([sum(x['price'] for x in it.get('expenses', [])) for it in items])
    c1, c2 = st.columns(2)
    c1.metric("預算", f"¥{tc:,}")
    c2.metric("支出", f"¥{ta:,}", delta=f"{tc-ta:,}" if ta>0 else None)
    if tc > 0 and ta > 0: st.progress(min(ta/tc, 1.0))

    # 天氣
    floc = items[0]['loc'] if items and items[0]['loc'] else "City"
    w = WeatherService.get_forecast(floc, curr_d)
    st.markdown(f"""<div class="apple-weather"><div style="display:flex;align-items:center;gap:15px;"><div style="font-size:2.5rem;">{w['icon']}</div><div><div style="font-size:2rem;font-weight:700;">{w['high']}°</div><div>L:{w['low']}°</div></div></div><div style="text-align:right;"><div style="font-weight:700;">{curr_d.strftime('%m/%d')}</div><div>📍 {floc}</div><div>{w['desc']}</div></div></div>""", unsafe_allow_html=True)

    is_edit = st.toggle("編輯模式 (含收據)")
    if is_edit and st.button("➕ 新增"):
        st.session_state.trip_data[day].append({"id": int(time.time()*1000), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "note": "", "expenses": [], "trans_mode": "📍", "trans_min": 30})
        st.rerun()

    if not items: st.info("尚無行程")

    for i, item in enumerate(items):
        # Card Content
        mlink = get_map_link(item['loc'])
        mbtn = f'<a href="{mlink}" target="_blank" style="text-decoration:none;margin-left:5px;font-size:0.8rem;background:{cur["secondary"]};color:{cur["text"]};padding:2px 6px;border-radius:6px;">🗺️</a>' if item['loc'] else ""
        cost_tg = f'<span style="background:{cur["primary"]};color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:bold;">¥{item["cost"]:,}</span>' if item['cost']>0 else ""
        
        exp_htm = ""
        if item.get('expenses'):
            rows = "".join([f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#888;'><span>{e['name']}</span><span>¥{e['price']:,}</span></div>" for e in item['expenses']])
            exp_htm = f"<div style='margin-top:8px;padding-top:5px;border-top:1px dashed #EEE;'>{rows}</div>"

        # Itinerary Card HTML
        st.markdown(f"""
        <div style="display:flex;gap:15px;">
            <div style="display:flex;flex-direction:column;align-items:center;width:50px;">
                <div style="font-weight:700;color:{cur['text']};font-size:1rem;">{item['time']}</div>
                <div style="flex-grow:1;width:2px;background:{cur['secondary']};margin:5px 0;opacity:0.4;"></div>
            </div>
            <div style="flex-grow:1;">
                <div class="apple-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div style="font-weight:bold;font-size:1.1rem;margin-bottom:4px;">{item['title']}</div>
                        {cost_tg}
                    </div>
                    <div style="font-size:0.9rem;color:{cur['sub']};">📍 {item['loc'] or '未設定'} {mbtn}</div>
                    <div style="font-size:0.85rem;color:{cur['sub']};background:{cur['bg']};padding:6px 10px;border-radius:8px;margin-top:6px;">📝 {item['note']}</div>
                    {exp_htm}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if is_edit:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                item['title'] = c1.text_input("名", item['title'], key=f"t_{item['id']}")
                item['time'] = c2.text_input("時", item['time'], key=f"tm_{item['id']}")
                item['loc'] = st.text_input("地", item['loc'], key=f"l_{item['id']}")
                item['cost'] = st.number_input("算", value=item['cost'], step=100, key=f"c_{item['id']}")
                item['note'] =
