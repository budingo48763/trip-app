import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd

# -------------------------------------
# 1. 系統設定 & 主題定義
# -------------------------------------
st.set_page_config(page_title="2026 旅程規劃", page_icon="✈️", layout="centered", initial_sidebar_state="collapsed")

# 🎨 主題配色庫 (莫蘭迪色系與經典風格)
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
    },
    "🌸 莫蘭迪·煙燻粉": {
        "bg": "#FFF5F7", "card": "#FFFFFF", "text": "#4F2C33", "primary": "#B0707D", "secondary": "#E8CUC9", "sub": "#85525C"
    },
    "🌊 鎌倉·海風藍": {
        "bg": "#F0F7FA", "card": "#FFFFFF", "text": "#0E2F44", "primary": "#2B6CB0", "secondary": "#BEE3F8", "sub": "#4299E1"
    },
    "🍵 宇治·抹茶": {
        "bg": "#F7FAF5", "card": "#FFFFFF", "text": "#1C3318", "primary": "#557C55", "secondary": "#C6EBC5", "sub": "#405D40"
    },
    "🍠 江戶·紫鳶": {
        "bg": "#F8F5FA", "card": "#FFFFFF", "text": "#2D2436", "primary": "#6B4C75", "secondary": "#D6BCFA", "sub": "#553C9A"
    },
    "🌑 現代·極簡灰": {
        "bg": "#F5F5F5", "card": "#FFFFFF", "text": "#1A1A1A", "primary": "#4A4A4A", "secondary": "#CCCCCC", "sub": "#666666"
    },
    "🍊 瀨戶內·暖陽": {
        "bg": "#FFFBF0", "card": "#FFFFFF", "text": "#453010", "primary": "#D69E2E", "secondary": "#FCE588", "sub": "#975A16"
    }
}

# -------------------------------------
# 2. 核心功能函數 & 資料定義
# -------------------------------------

LOCATION_DB = {
    "京都車站": (34.98, 135.75),
    "KOKO HOTEL 京都": (34.98, 135.76),
    "清水寺": (34.99, 135.78),
    "八坂神社": (35.00, 135.77),
    "伏見稻荷大社": (34.96, 135.77),
    "金閣寺": (35.03, 135.72),
    "嵐山": (35.01, 135.67),
    "二條城": (35.01, 135.74),
    "大阪城": (34.68, 135.52),
    "環球影城": (34.66, 135.43),
    "心齋橋": (34.67, 135.50),
    "奈良公園": (34.68, 135.84),
    "關西機場": (34.43, 135.23)
}

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船", "✈️ 飛機"]

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
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(location)}"

def generate_google_map_route(items):
    valid_locs = [item['loc'] for item in items if item.get('loc') and item['loc'].strip()]
    if len(valid_locs) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    encoded_locs = [urllib.parse.quote(loc) for loc in valid_locs]
    return base_url + "/".join(encoded_locs)

def get_category_icon(cat):
    icons = {"trans": "🚃", "food": "🍱", "stay": "🏨", "spot": "⛩️", "shop": "🛍️", "other": "📍"}
    return icons.get(cat, "📍")

def process_excel_upload(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        required_cols = ['Day', 'Time', 'Title']
        if not all(col in df.columns for col in required_cols):
            st.error("Excel 格式錯誤：缺少 Day, Time 或 Title 欄位")
            return
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

# 獲取當前主題顏色
current_theme = THEMES[st.session_state.selected_theme_name]

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "time": "10:00", "title": "抵達關西機場", "loc": "關西機場", "cost": 0, "cat": "trans", "note": "入境審查、領取周遊券", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 75},
            {"id": 102, "time": "13:00", "title": "京都車站 Check-in", "loc": "KOKO HOTEL 京都", "cost": 0, "cat": "stay", "note": "寄放行李", "expenses": [], "trans_mode": "🚌 巴士", "trans_min": 20},
            {"id": 103, "time": "15:00", "title": "錦市場", "loc": "錦市場", "cost": 2000, "cat": "food", "note": "吃午餐、玉子燒、豆乳甜甜圈", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 104, "time": "18:00", "title": "鴨川散步", "loc": "鴨川", "cost": 0, "cat": "spot", "note": "欣賞夜景", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
        ],
        2: [
            {"id": 201, "time": "09:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "cat": "spot", "note": "著名的清水舞台，早點去避開人潮", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 20},
            {"id": 202, "time": "11:00", "title": "二三年坂", "loc": "三年坂", "cost": 1000, "cat": "spot", "note": "古色古香的街道，買伴手禮", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 203, "time": "13:00", "title": "八坂神社", "loc": "八坂神社", "cost": 0, "cat": "spot", "note": "祈求良緣", "expenses": [], "trans_mode": "🚌 巴士", "trans_min": 30},
            {"id": 204, "time": "16:00", "title": "金閣寺", "loc": "金閣寺", "cost": 400, "cat": "spot", "note": "夕陽下的金閣寺最美", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
        ],
        3: [
            {"id": 301, "time": "09:00", "title": "伏見稻荷大社", "loc": "伏見稻荷大社", "cost": 0, "cat": "spot", "note": "千本鳥居拍照", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 45},
            {"id": 302, "time": "13:00", "title": "奈良公園", "loc": "奈良公園", "cost": 200, "cat": "spot", "note": "買鹿餅餵鹿 (小心被咬)", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 303, "time": "15:00", "title": "東大寺", "loc": "東大寺", "cost": 600, "cat": "spot", "note": "看巨大佛像", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 60},
            {"id": 304, "time": "19:00", "title": "移動至大阪", "loc": "大阪", "cost": 0, "cat": "trans", "note": "入住大阪飯店", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
        ],
        4: [
            {"id": 401, "time": "09:30", "title": "環球影城 (USJ)", "loc": "環球影城", "cost": 9000, "cat": "spot", "note": "馬利歐園區需抽整理券", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 40},
            {"id": 402, "time": "19:00", "title": "道頓堀", "loc": "道頓堀", "cost": 3000, "cat": "food", "note": "跑跑人看板、吃章魚燒、拉麵", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
        ],
        5: [
            {"id": 501, "time": "10:00", "title": "黑門市場", "loc": "黑門市場", "cost": 2000, "cat": "food", "note": "大阪的廚房，吃海鮮", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 50},
            {"id": 502, "time": "13:00", "title": "臨空城 Outlet", "loc": "Rinku Premium Outlets", "cost": 10000, "cat": "shop", "note": "最後採買", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 20},
            {"id": 503, "time": "16:00", "title": "前往機場", "loc": "關西機場", "cost": 0, "cat": "trans", "note": "搭機返台", "expenses": [], "trans_mode": "✈️ 飛機", "trans_min": 0}
        ]
    }

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {
        "outbound": {"date": "1/17", "code": "JX821", "dep": "10:00", "arr": "13:30", "dep_loc": "桃機 T1", "arr_loc": "關西機場"},
        "inbound": {"date": "1/22", "code": "JX822", "dep": "15:00", "arr": "17:10", "dep_loc": "關西機場", "arr_loc": "桃機 T1"}
    }

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [
        {"id": 1, "name": "KOKO HOTEL 京都", "range": "D1-D3 (3泊)", "date": "1/17 - 1/19", "addr": "京都府京都市...", "link": "https://goo.gl/maps/example"},
        {"id": 2, "name": "相鐵 FRESA INN 大阪", "range": "D4-D5 (2泊)", "date": "1/20 - 1/21", "addr": "大阪府大阪市...", "link": "https://goo.gl/maps/example"}
    ]

default_checklist = {
    "必要證件": {"護照": False, "機票證明": False, "Visit Japan Web": False, "日幣現金": False, "信用卡": False},
    "電子產品": {"手機 & 充電線": False, "行動電源": False, "SIM卡 / Wifi機": False, "轉接頭": False},
    "衣物穿搭": {"換洗衣物": False, "睡衣": False, "好走的鞋子": False, "外套": False},
    "生活用品": {"牙刷牙膏": False, "常備藥": False, "塑膠袋": False, "折疊傘": False}
}
if "checklist" not in st.session_state or not isinstance(st.session_state.checklist.get("必要證件"), dict):
    st.session_state.checklist = default_checklist

# -------------------------------------
# 4. CSS 樣式 (動態主題)
# -------------------------------------
# 使用 f-string 將 current_theme 的顏色變數注入 CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp {{ 
        background-color: {current_theme['bg']} !important;
        color: {current_theme['text']} !important; 
        font-family: 'Noto Serif JP', 'Times New Roman', serif !important;
    }}

    [data-testid="stSidebarCollapsedControl"], section[data-testid="stSidebar"], 
    div[data-testid="stToolbar"], div[data-testid="stDecoration"], footer {{
        display: none !important;
    }}
    header[data-testid="stHeader"] {{ height: 0 !important; background: transparent !important; }}

    /* --- Day 按鈕 --- */
    div[data-testid="stRadio"] > div {{
        display: flex !important; flex-direction: row !important; overflow-x: auto !important;
        flex-wrap: nowrap !important; gap: 10px !important; padding-bottom: 5px !important;
    }}
    div[data-testid="stRadio"] label {{
        background-color: {current_theme['card']} !important; 
        border: 1px solid #E0E0E0 !important;
        min-width: 60px !important; width: 60px !important; height: 75px !important;
        border-radius: 8px !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        margin-right: 0px !important; padding: 5px !important;
        justify-content: center !important; align-items: center !important; text-align: center !important;
    }}
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {{
        font-family: 'Times New Roman', serif !important; font-size: 1.6rem !important;
        font-weight: 500 !important; color: {current_theme['sub']} !important; line-height: 1.1 !important; margin: 0 !important;
    }}
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p::first-line {{
        font-size: 0.8rem !important; color: #AAA !important; font-weight: 400 !important;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] {{
        background-color: {current_theme['primary']} !important; 
        border: 1px solid {current_theme['primary']} !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important; transform: translateY(-2px);
    }}
    div[data-testid="stRadio"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {{ color: #FFFFFF !important; }}
    div[data-testid="stRadio"] label > div:first-child {{ display: none !important; }}

    /* --- 行程卡片與時間軸 --- */
    .timeline-wrapper {{ position: relative; padding-left: 75px; }}
    
    .itinerary-card {{
        background: {current_theme['card']}; border: 1px solid #F0F0F0; border-radius: 12px;
        padding: 15px; margin-bottom: 0px; position: relative;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03); z-index: 2;
    }}
    .time-dot {{
        position: absolute; left: -26px; top: 20px; width: 12px; height: 12px;
        background-color: {current_theme['text']}; border-radius: 50%; z-index: 2; border: 2px solid {current_theme['bg']};
    }}
    .time-label {{
        position: absolute; left: -80px; top: 15px; width: 60px; text-align: right;
        font-size: 0.95rem; font-weight: 900; color: {current_theme['sub']}; font-family: 'Times New Roman', sans-serif;
    }}
    .connector-line {{
        border-left: 2px dashed {current_theme['secondary']}; margin-left: -21px; padding-left: 21px;
        padding-top: 15px; padding-bottom: 15px; min-height: 40px; position: relative; z-index: 1;
        display: flex; align-items: center;
    }}
    .travel-badge {{
        background-color: {current_theme['card']}; border: 1px solid #EEE; border-radius: 6px;
        padding: 5px 10px; display: inline-block; font-size: 0.8rem; color: {current_theme['sub']};
        font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-left: 10px;
    }}
    .card-title {{ font-size: 1.2rem; font-weight: 900; color: {current_theme['text']}; margin-bottom: 4px; }}
    .card-sub {{ font-size: 0.9rem; color: {current_theme['sub']}; display: flex; align-items: center; gap: 5px; }}
    .card-tag {{ background: {current_theme['primary']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: auto;}}
    
    /* 地圖按鈕 */
    .map-btn {{
        text-decoration: none; color: {current_theme['sub']}; border: 1px solid #EEE; 
        padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; 
        margin-left: 8px; background: {current_theme['bg']}; display: inline-flex; align-items: center;
    }}
    .map-btn:hover {{ background: #F0F0F0; }}

    /* 記帳與筆記區塊 */
    .expense-box {{
        background-color: {current_theme['bg']}; border-top: 1px solid #EEE; margin-top: 10px; padding-top: 10px;
    }}
    .expense-item {{
        display: flex; justify-content: space-between; font-size: 0.85rem; color: {current_theme['text']}; margin-bottom: 4px; border-bottom: 1px dashed #EEE; padding-bottom: 2px;
    }}
    .expense-note {{
        font-size: 0.85rem; color: {current_theme['sub']}; background: {current_theme['bg']}; padding: 5px 8px; border-radius: 4px; margin-bottom: 8px; border: 1px solid #EEE;
    }}

    /* 重要資訊卡片 */
    .info-card {{
        background-color: {current_theme['card']}; border-radius: 12px; padding: 20px; margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #F0F0F0;
    }}
    .info-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: {current_theme['sub']}; font-size: 0.85rem; font-weight: bold; }}
    .info-time {{ font-size: 1.8rem; font-weight: 900; color: {current_theme['text']}; margin-bottom: 5px; font-family: 'Times New Roman', serif; }}
    .info-loc {{ color: {current_theme['sub']}; font-size: 0.9rem; display: flex; align-items: center; gap: 5px; }}
    .info-tag {{ background: {current_theme['bg']}; color: {current_theme['sub']}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
    
    /* 路線全覽動畫 */
    .map-tl-container {{ position: relative; max-width: 100%; margin: 20px auto; padding-left: 30px; }}
    .map-tl-container::before {{
        content: ''; position: absolute; top: 0; bottom: 0; left: 14px; width: 2px;
        background-image: linear-gradient({current_theme['primary']} 40%, rgba(255,255,255,0) 0%);
        background-position: right; background-size: 2px 12px; background-repeat: repeat-y;
    }}
    .map-tl-item {{ position: relative; margin-bottom: 25px; animation: fadeInUp 0.6s ease-in-out both; }}
    .map-tl-icon {{
        position: absolute; left: -31px; top: 0px; width: 32px; height: 32px;
        background: {current_theme['card']}; border: 2px solid {current_theme['primary']}; border-radius: 50%;
        text-align: center; line-height: 28px; font-size: 16px; z-index: 2;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .map-tl-content {{
        background: {current_theme['card']}; border: 1px solid #E0E0E0; border-left: 4px solid {current_theme['primary']};
        padding: 12px 15px; border-radius: 4px; box-shadow: 0 3px 6px rgba(0,0,0,0.05);
    }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translate3d(0, 20px, 0); }} to {{ opacity: 1; transform: translate3d(0, 0, 0); }} }}

    /* UI Tweaks */
    button[data-baseweb="tab"] {{ color: {current_theme['sub']}; border-bottom: 2px solid transparent; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {current_theme['primary']}; border-bottom: 3px solid {current_theme['primary']}; font-weight: bold; }}
    div[data-baseweb="input"], div[data-baseweb="base-input"] {{ border: none !important; border-bottom: 1px solid {current_theme['secondary']} !important; background: transparent !important; }}
    input {{ color: {current_theme['text']} !important; }}
    
    /* 進度條顏色 */
    div[data-testid="stProgress"] > div > div {{ background-color: {current_theme['primary']} !important; }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 5. 主畫面
# -------------------------------------
st.markdown(f'<div style="font-size:2.5rem; font-weight:900; text-align:center; margin-bottom:5px; color:{current_theme["text"]};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown(f'<div style="text-align:center; color:{current_theme["sub"]}; font-size:0.9rem; margin-bottom:20px;">1/17 - 1/22</div>', unsafe_allow_html=True)

# --- Settings Expander ---
with st.expander("⚙️ 旅程設定 & 主題"):
    st.session_state.trip_title = st.text_input("旅程標題", value=st.session_state.trip_title)
    
    # 主題選擇器
    st.markdown("**🎨 選擇主題風格**")
    theme_name = st.selectbox("主題", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.selected_theme_name), label_visibility="collapsed")
    if theme_name != st.session_state.selected_theme_name:
        st.session_state.selected_theme_name = theme_name
        st.rerun() # 立即刷新以套用顏色

    c_set1, c_set2 = st.columns(2)
    with c_set1: start_date = st.date_input("出發日期", value=datetime.today())
    with c_set2: st.session_state.exchange_rate = st.number_input("匯率 (JPY->TWD)", value=st.session_state.exchange_rate, step=0.001, format="%.3f")
    
    c_set3, c_set4 = st.columns(2)
    with c_set3: st.session_state.trip_days_count = st.number_input("旅遊天數", 1, 30, st.session_state.trip_days_count)
    with c_set4: st.session_state.target_country = st.selectbox("旅遊地區 (影響資訊)", ["日本", "韓國", "泰國", "台灣"])
    
    st.markdown("---")
    st.caption("📥 匯入 Excel (欄位: Day, Time, Title, Location, Cost, Note)")
    uploaded_file = st.file_uploader("上傳 .xlsx", type=["xlsx"], label_visibility="collapsed")
    if uploaded_file:
        if st.button("確認匯入"): process_excel_upload(uploaded_file)

# 確保天數資料存在
for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

tab1, tab2, tab3, tab4 = st.tabs(["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單", "ℹ️ 重要資訊"])

# ==========================================
# 1. 行程規劃
# ==========================================
with tab1:
    selected_day_num = st.radio("DaySelect", list(range(1, st.session_state.trip_days_count + 1)), index=0, horizontal=False, label_visibility="collapsed", format_func=lambda x: f"Day\n{x}")
    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]
    current_items = st.session_state.trip_data[selected_day_num]
    
    current_items.sort(key=lambda x: x['time'])

    st.markdown(f"<div style='font-size:2rem; font-weight:900; font-family:Times New Roman; color:{current_theme['text']};'>Day {selected_day_num}</div>", unsafe_allow_html=True)
    st.caption(f"{date_str} {week_str}")

    is_edit_mode = st.toggle("✏️ 編輯模式", value=False, key="main_edit")

    if is_edit_mode:
        if st.button("➕ 新增行程", type="primary", use_container_width=True):
            st.session_state.trip_data[selected_day_num].append({"id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": "", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30})
            st.rerun()

    st.markdown('<div class="timeline-wrapper" style="margin-top:20px;">', unsafe_allow_html=True)
    
    if not current_items:
        st.info("🍵 點擊「編輯模式」開始安排今日行程")

    for index, item in enumerate(current_items):
        icon = get_category_icon(item['cat'])
        
        if "expenses" not in item: item["expenses"] = []
        if "trans_min" not in item: item["trans_min"] = 30
        
        current_expense_sum = sum(x['price'] for x in item['expenses'])
        display_cost = current_expense_sum if current_expense_sum > 0 else item['cost']
        
        if display_cost > 0:
            twd_val = int(display_cost * st.session_state.exchange_rate)
            price_tag = f"¥{display_cost:,} <span style='font-size:0.7rem; opacity:0.8;'>(NT${twd_val:,})</span>"
        else:
            price_tag = ""
        
        note_html = f"<div class='expense-note'>📝 {item['note']}</div>" if item['note'] and not is_edit_mode else ""

        expense_block = ""
        if item['expenses']:
            rows = []
            for exp in item['expenses']:
                exp_twd = int(exp['price'] * st.session_state.exchange_rate)
                rows.append(f"<div class='expense-item'><span>{exp['name']}</span><span>¥{exp['price']:,} (NT${exp_twd})</span></div>")
            expense_block = f"<div class='expense-box'>{''.join(rows)}</div>"

        map_link = get_single_map_link(item['loc'])
        map_icon_html = f'<a href="{map_link}" target="_blank" class="map-btn">🗺️ 地圖</a>' if item['loc'] else ""

        card_html = f"""<div style="position:relative;"><div class="time-label">{item['time']}</div><div class="time-dot"></div><div class="itinerary-card"><div class="card-title">{icon} {item['title']}</div><div class="card-sub"><span>📍 {item['loc'] if item['loc'] else '未設定地點'}</span>{map_icon_html}<span class="card-tag" style="margin-left:auto;">{price_tag}</span></div>{note_html}{expense_block}</div></div>"""
        
        st.markdown(card_html, unsafe_allow_html=True)

        if is_edit_mode:
            with st.container(border=True):
                st.caption(f"編輯：{item['title']}")
                item['note'] = st.text_area("備註", item['note'], height=68, key=f"note_{item['id']}")
                c_ex_n, c_ex_p, c_ex_btn = st.columns([3, 2, 1])
                c_ex_n.text_input("項目", key=f"new_exp_n_{item['id']}", placeholder="項目", label_visibility="collapsed")
                c_ex_p.number_input("金額", min_value=0, step=100, key=f"new_exp_p_{item['id']}", label_visibility="collapsed")
                c_ex_btn.button("➕", key=f"add_exp_btn_{item['id']}", on_click=add_expense_callback, args=(item['id'], selected_day_num))
                
                if item['expenses']:
                    with st.expander("管理明細"):
                        for i_exp, exp in enumerate(item['expenses']):
                            c_d1, c_d2 = st.columns([4, 1])
                            c_d1.text(f"{exp['name']} ¥{exp['price']}")
                            if c_d2.button("🗑️", key=f"del_exp_{item['id']}_{i_exp}"):
                                item['expenses'].pop(i_exp)
                                st.rerun()
                st.divider()
                c1, c2 = st.columns(2)
                item['title'] = c1.text_input("名稱", item['title'], key=f"t_{item['id']}")
                item['loc'] = c2.text_input("地點", item['loc'], key=f"l_{item['id']}")
                try: t_obj = datetime.strptime(item['time'], "%H:%M").time()
                except: t_obj = datetime.strptime("09:00", "%H:%M").time()
                item['time'] = c1.time_input("時間", value=t_obj, key=f"tm_{item['id']}").strftime("%H:%M")
                item['cost'] = c2.number_input("預算", value=item['cost'], step=100, key=f"c_{item['id']}")
                if st.button("🗑️ 刪除此行程", key=f"del_{item['id']}"):
                    st.session_state.trip_data[selected_day_num].pop(index)
                    st.rerun()

        if index < len(current_items) - 1:
            if "trans_mode" not in item: item["trans_mode"] = "📍 移動"
            current_min_total = item['trans_min']
            current_h = current_min_total // 60
            current_m = current_min_total % 60

            if is_edit_mode:
                st.markdown('<div class="connector-line">', unsafe_allow_html=True)
                c_t1, c_t2, c_t3 = st.columns([2, 1, 1])
                item['trans_mode'] = c_t1.selectbox("交通", TRANSPORT_OPTIONS, index=0 if item['trans_mode'] not in TRANSPORT_OPTIONS else TRANSPORT_OPTIONS.index(item['trans_mode']), key=f"tr_m_{item['id']}", label_visibility="collapsed")
                new_h = c_t2.number_input("時", value=current_h, min_value=0, max_value=12, key=f"tr_h_{item['id']}", label_visibility="collapsed")
                new_m = c_t3.number_input("分", value=current_m, min_value=0, max_value=59, step=5, key=f"tr_mn_{item['id']}", label_visibility="collapsed")
                item['trans_min'] = new_h * 60 + new_m
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                time_display = f"{current_m} 分"
                if current_h > 0: time_display = f"{current_h} 小時 {current_m} 分"
                travel_info = f"{item['trans_mode']} 約 {time_display}"
                st.markdown(f'<div class="connector-line"><span class="travel-badge">{travel_info}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if current_items:
        st.markdown("---")
        route_url = generate_google_map_route(current_items)
        st.markdown(f"<div style='text-align:center;'><a href='{route_url}' target='_blank' style='background:{current_theme['primary']}; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 開啟本日導航 (Google Maps)</a></div>", unsafe_allow_html=True)

# ==========================================
# 2. 路線全覽
# ==========================================
with tab2:
    st.markdown(f'<div class="retro-subtitle" style="font-weight:900; color:{current_theme["sub"]}; text-align:center; margin-bottom:15px; letter-spacing:1px;">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
    map_day = st.selectbox("選擇天數", list(range(1, st.session_state.trip_days_count + 1)), format_func=lambda x: f"Day {x}")
    map_items = sorted(st.session_state.trip_data[map_day], key=lambda x: x['time'])
    
    if map_items:
        t_html = ['<div class="map-tl-container">']
        for i, item in enumerate(map_items):
            icon = get_category_icon(item.get('cat', 'other'))
            loc_text = f"📍 {item['loc']}" if item['loc'] else ""
            t_html.append(f"""
            <div class='map-tl-item' style='animation-delay:{i*0.1}s'>
                <div class='map-tl-icon'>{icon}</div>
                <div class='map-tl-content'>
                    <div style='color:{current_theme['primary']}; font-weight:bold;'>{item['time']}</div>
                    <div style='font-weight:900; font-size:1.1rem; color:{current_theme['text']};'>{item['title']}</div>
                    <div style='font-size:0.85rem; color:{current_theme['sub']};'>{loc_text}</div>
                </div>
            </div>""")
        t_html.append('</div>')
        st.markdown("".join(t_html), unsafe_allow_html=True)
    else:
        st.info("🌸 本日尚無行程")

# ==========================================
# 3. 準備清單
# ==========================================
with tab3:
    c_list_head, c_list_edit = st.columns([3, 1])
    c_list_head.markdown("### 🎒 行李檢查表")
    edit_list_mode = c_list_edit.toggle("編輯清單")

    for category in list(st.session_state.checklist.keys()):
        st.markdown(f"**{category}**")
        items = st.session_state.checklist[category]
        cols = st.columns(2)
        keys_to_delete = []
        for i, (item, checked) in enumerate(items.items()):
            col = cols[i % 2]
            if edit_list_mode:
                c_e1, c_e2 = col.columns([4, 1])
                c_e1.text(item)
                if c_e2.button("x", key=f"del_chk_{category}_{item}"):
                    keys_to_delete.append(item)
            else:
                is_checked = col.checkbox(item, value=checked, key=f"chk_{category}_{item}")
                st.session_state.checklist[category][item] = is_checked
        
        if keys_to_delete:
            for k in keys_to_delete: del st.session_state.checklist[category][k]
            st.rerun()

        if edit_list_mode:
            new_item = st.text_input(f"新增至 {category}", key=f"new_item_{category}", placeholder="項目名稱")
            if new_item and st.button("加入", key=f"add_btn_{category}"):
                st.session_state.checklist[category][new_item] = False
                st.rerun()
            if st.button(f"刪除分類 {category}", key=f"del_cat_{category}"):
                 del st.session_state.checklist[category]
                 st.rerun()

    if edit_list_mode:
        st.markdown("---")
        new_cat = st.text_input("新增分類名稱", placeholder="例如: 攝影器材")
        if new_cat and st.button("新增分類"):
            st.session_state.checklist[new_cat] = {}
            st.rerun()

    st.markdown("---")
    country = st.session_state.target_country
    st.markdown(f"### 🌍 當地旅遊資訊 ({country})")
    
    trip_month = start_date.month
    season_info = ""
    weather_icon = "🌤️"
    
    if 3 <= trip_month <= 5:
        season_info = "春季：氣候宜人但早晚偏涼，適合洋蔥式穿搭，建議帶一件薄外套。"
        weather_icon = "🌸"
    elif 6 <= trip_month <= 8:
        season_info = "夏季：炎熱潮濕，注意防曬與補充水分，室內冷氣較強，可帶薄衫。"
        weather_icon = "☀️"
    elif 9 <= trip_month <= 11:
        season_info = "秋季：涼爽舒適，是旅遊的最佳季節，建議長袖衣物搭配外套。"
        weather_icon = "🍁"
    else:
        season_info = "冬季：寒冷乾燥，需準備保暖大衣、圍巾與手套。"
        weather_icon = "❄️"
    
    voltage_info = "100V (雙平腳)"
    sos_info = "警察 110 / 救護 119"
    tip_info = "無小費文化，餐廳含稅。"
    
    if country == "韓國":
        voltage_info = "220V (兩孔圓形)"
        sos_info = "警察 112 / 救護 119"
    elif country == "泰國":
        voltage_info = "220V (雙平腳/兩孔圓)"
        sos_info = "觀光警察 1155"
        tip_info = "有小費習慣，按摩約 50-100 泰銖。"
    elif country == "台灣":
        voltage_info = "110V (雙平腳)"
        sos_info = "警察 110 / 救護 119"
        season_info = "四季溫暖潮濕，夏季多颱風。"

    info_cols = st.columns(2)
    with info_cols[0]:
        st.info(f"**{weather_icon} {trip_month}月氣候建議**\n\n{season_info}")
        st.success(f"**🔌 電壓**\n\n{voltage_info}")
    with info_cols[1]:
        st.warning(f"**🚑 緊急電話**\n\n{sos_info}")
        st.error(f"**💴 小費與消費**\n\n{tip_info}")

# ==========================================
# 4. 重要資訊
# ==========================================
with tab4:
    col_info_head, col_info_edit = st.columns([3, 1])
    with col_info_head: st.markdown("### ✈️ 航班")
    with col_info_edit: info_edit_mode = st.toggle("編輯", key="info_edit_toggle")

    flights = st.session_state.flight_info
    
    # 去程
    out_f = flights["outbound"]
    if info_edit_mode:
        with st.container(border=True):
            st.caption("編輯去程")
            c1, c2 = st.columns(2)
            out_f["date"] = c1.text_input("日期", out_f["date"], key="fd_1")
            out_f["code"] = c2.text_input("航班號", out_f["code"], key="fc_1")
            out_f["dep"] = c1.text_input("起飛時間", out_f["dep"], key="ft_1")
            out_f["arr"] = c2.text_input("抵達時間", out_f["arr"], key="ft_2")
            out_f["dep_loc"] = c1.text_input("起飛機場", out_f["dep_loc"], key="fl_1")
            out_f["arr_loc"] = c2.text_input("抵達機場", out_f["arr_loc"], key="fl_2")
    
    st.markdown(f"""<div class="info-card"><div class="info-header"><span>📅 {out_f['date']}</span> <span>✈️ {out_f['code']}</span></div><div class="info-time">{out_f['dep']} -> {out_f['arr']}</div><div class="info-loc"><span>📍 {out_f['dep_loc']}</span> <span style="margin:0 5px;">✈</span> <span>{out_f['arr_loc']}</span></div><div style="text-align:right; margin-top:5px;"><span class="info-tag">去程</span></div></div>""", unsafe_allow_html=True)

    # 回程
    in_f = flights["inbound"]
    if info_edit_mode:
        with st.container(border=True):
            st.caption("編輯回程")
            c1, c2 = st.columns(2)
            in_f["date"] = c1.text_input("日期", in_f["date"], key="fd_3")
            in_f["code"] = c2.text_input("航班號", in_f["code"], key="fc_2")
            in_f["dep"] = c1.text_input("起飛時間", in_f["dep"], key="ft_3")
            in_f["arr"] = c2.text_input("抵達時間", in_f["arr"], key="ft_4")
            in_f["dep_loc"] = c1.text_input("起飛機場", in_f["dep_loc"], key="fl_3")
            in_f["arr_loc"] = c2.text_input("抵達機場", in_f["arr_loc"], key="fl_4")

    st.markdown(f"""<div class="info-card"><div class="info-header"><span>📅 {in_f['date']}</span> <span>✈️ {in_f['code']}</span></div><div class="info-time">{in_f['dep']} -> {in_f['arr']}</div><div class="info-loc"><span>📍 {in_f['dep_loc']}</span> <span style="margin:0 5px;">✈</span> <span>{in_f['arr_loc']}</span></div><div style="text-align:right; margin-top:5px;"><span class="info-tag">回程</span></div></div>""", unsafe_allow_html=True)

    st.divider()

    col_hotel_head, _ = st.columns([3, 1])
    with col_hotel_head: st.markdown("### 🏨 住宿")

    if info_edit_mode:
        if st.button("➕ 新增住宿"):
            st.session_state.hotel_info.append({"id": int(time.time()), "name": "新住宿", "range": "D?-D?", "date": "", "addr": "", "link": ""})
            st.rerun()

    for i, hotel in enumerate(st.session_state.hotel_info):
        if info_edit_mode:
            with st.expander(f"編輯: {hotel['name']}", expanded=True):
                hotel['range'] = st.text_input("天數標記", hotel['range'], key=f"h_r_{hotel['id']}")
                hotel['date'] = st.text_input("日期範圍", hotel['date'], key=f"h_d_{hotel['id']}")
                hotel['name'] = st.text_input("飯店名稱", hotel['name'], key=f"h_n_{hotel['id']}")
                hotel['addr'] = st.text_input("地址", hotel['addr'], key=f"h_a_{hotel['id']}")
                hotel['link'] = st.text_input("地圖連結", hotel['link'], key=f"h_l_{hotel['id']}")
                if st.button("🗑️ 刪除此住宿", key=f"del_h_{hotel['id']}"):
                    st.session_state.hotel_info.pop(i)
                    st.rerun()

        # 安全的單行 HTML 寫法
        hotel_html = f"""<div class="info-card" style="border-left: 5px solid {current_theme['primary']};"><div class="info-header"><span class="info-tag" style="background:{current_theme['primary']}; color:white;">{hotel['range']}</span><span>{hotel['date']}</span></div><div style="font-size:1.3rem; font-weight:900; color:{current_theme['text']}; margin: 10px 0;">{hotel['name']}</div><div class="info-loc" style="margin-bottom:10px;">📍 {hotel['addr']}</div><a href="{hotel['link']}" target="_blank" style="text-decoration:none; color:{current_theme['primary']}; font-size:0.9rem; font-weight:bold; border:1px solid {current_theme['primary']}; padding:4px 12px; border-radius:20px;">🗺️ 地圖</a></div>"""
        st.markdown(hotel_html, unsafe_allow_html=True)