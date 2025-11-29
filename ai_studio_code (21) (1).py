import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
import random
import json
import base64
import re

# --- 嘗試匯入進階套件 ---
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    CLOUD_AVAILABLE = True
except ImportError:
    CLOUD_AVAILABLE = False

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

DEFAULT_RATES = {
    "日本": 0.2150, "韓國": 0.0235, "泰國": 0.9500, "台灣": 1.0000
}

# -------------------------------------
# 2. 核心功能函數
# -------------------------------------

def get_gemini_model():
    if not GEMINI_AVAILABLE: return None
    if "GEMINI_API_KEY" not in st.secrets: return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        priority_models = [
            'gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.5-pro',
            'gemini-2.0-flash-lite', 'gemini-1.5-flash', 'gemini-pro'
        ]
        return genai.GenerativeModel(priority_models[0])
    except Exception as e:
        print(f"Model Init Error: {e}")
        return None

def get_ai_step_advice_stream(item, country):
    model = get_gemini_model()
    if not model:
        yield "⚠️ AI 未啟用 (請設定 API Key)"
        return
    try:
        prompt = f"""
        使用者正在 {country} 旅遊。
        當下行程：{item['title']} (地點: {item['loc']})
        備註：{item['note']}
        請提供約 100 字的簡短建議(注意事項、看點或美食)。
        """
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text: yield chunk.text
    except Exception as e:
        err_msg = str(e)
        if "404" in err_msg: yield "⚠️ 錯誤 404：找不到模型。"
        else: yield f"連線錯誤: {err_msg}"

def parse_wishlist_text(raw_text):
    model = get_gemini_model()
    if not model: return None
    try:
        prompt = f"""
        請分析以下文字（可能是 Google Maps 分享連結、Tabelog 店名、或一段網誌介紹），提取出旅遊景點資訊。
        文字內容：{raw_text}
        
        請回傳一個 JSON 物件 (Object)，包含以下欄位：
        - title: 景點或餐廳名稱
        - loc: 地址或大概區域 (如果沒有，留空)
        - note: 簡短的描述或評價 (從文字中摘要)
        
        只回傳 JSON，不要有 Markdown。
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Wishlist Parse Error: {e}")
        return None

def analyze_receipt_image(image_file):
    model = get_gemini_model()
    default_res = [{"name": "分析失敗", "price": 0}]
    if not model: return [{"name": "模擬商品(無AI)", "price": 100}]
    try:
        img = Image.open(image_file)
        prompt = "你是一個收據辨識助手。請分析這張圖片，列出商品名稱與金額(整數)。請排除小計、稅金、合計。請務必直接回傳一個 JSON Array，不要包含 ```json 或其他文字。格式範例：[{'name':'商品A', 'price':100}, {'name':'商品B', 'price':500}]"
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            return data if isinstance(data, list) else default_res
        else:
            text = text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            return data if isinstance(data, list) else default_res
    except Exception as e:
        print(f"OCR Error: {e}")
        return default_res

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
            return True, "儲存成功！"
        except Exception as e: return False, f"寫入失敗: {e}"
    return False, "連線失敗 (請檢查 secrets 設定)"

def load_from_cloud():
    client = get_cloud_connection()
    if client:
        try:
            sheet = client.open("TripPlanDB").sheet1
            return sheet.cell(1, 1).value
        except: return None
    return None

def generate_google_nav_link(origin, dest, mode="transit"):
    if not origin or not dest: return "#"
    base = "https://www.google.com/maps/dir/?api=1"
    return f"{base}&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(dest)}&travelmode={mode}"

def process_excel_upload(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        new_trip_data = {}
        for _, row in df.iterrows():
            day = int(row['Day'])
            if day not in new_trip_data: new_trip_data[day] = []
            new_trip_data[day].append({
                "id": int(time.time()*1000)+random.randint(0,1000), 
                "time": str(row['Time']), "title": str(row['Title']),
                "loc": str(row.get('Location','')), "cost": int(row.get('Cost',0)), 
                "note": str(row.get('Note','')), "expenses": []
            })
        st.session_state.trip_data = new_trip_data
        st.session_state.trip_days_count = max(new_trip_data.keys())
        st.rerun()
    except Exception as e: 
        st.error(f"匯入失敗：{e}")

# -------------------------------------
# 3. 初始化 & 資料
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "target_country" not in st.session_state: st.session_state.target_country = "日本"
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "⛩️ 京都緋紅 (預設)"
if "start_date" not in st.session_state: st.session_state.start_date = datetime(2026, 1, 17)
if "show_ai_intro" not in st.session_state: st.session_state.show_ai_intro = True

if "wishlist" not in st.session_state:
    st.session_state.wishlist = [
        {"id": 901, "title": "HARBS 千層蛋糕", "loc": "大丸京都店", "note": "必吃水果千層"},
        {"id": 902, "title": " % Arabica 咖啡", "loc": "嵐山", "note": "網美打卡點"}
    ]
if "shopping_list" not in st.session_state:
    st.session_state.shopping_list = pd.DataFrame(columns=["對象", "商品名稱", "預算(¥)", "已購買"])

if "current_step_index" not in st.session_state:
    st.session_state.current_step_index = 0
if "ai_advice_cache" not in st.session_state:
    st.session_state.ai_advice_cache = {} 

default_checklist = {
    "必要證件": {"護照": False, "機票證明": False, "Visit Japan Web": False, "日幣現金": False},
    "電子產品": {"手機 & 充電線": False, "行動電源": False, "SIM卡 / Wifi機": False, "轉接頭": False},
    "衣物穿搭": {"換洗衣物": False, "睡衣": False, "好走的鞋子": False, "外套": False},
    "生活用品": {"牙刷牙膏": False, "常備藥": False, "塑膠袋": False, "折疊傘": False}
}
if "checklist" not in st.session_state or not isinstance(st.session_state.checklist, dict):
    st.session_state.checklist = default_checklist
elif not all(isinstance(v, dict) for v in st.session_state.checklist.values()):
    st.session_state.checklist = default_checklist

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

SURVIVAL_PHRASES = {
    "日本": {
        "👋 招呼": [("你好", "こんにちは"), ("謝謝", "ありがとう"), ("不好意思", "すみません"), ("是 / 不是", "はい / いいえ")],
        "🍜 點餐": [("請給我這個", "これをください"), ("多少錢", "いくらですか"), ("結帳", "お会計お願いします"), ("好吃的", "おいしい")],
        "🚆 交通": [("...在哪裡？", "…はどこですか？"), ("車站", "駅"), ("廁所", "トイレ"), ("請帶我去", "連れて行って")]
    },
    "韓國": {
        "👋 招呼": [("你好", "안녕하세요"), ("謝謝", "감사합니다"), ("對不起", "미안합니다")],
        "🍜 點餐": [("請給我這個", "이거 주세요"), ("多少錢", "얼마예요?"), ("買單", "계산해 주세요")],
        "🚆 交通": [("...在哪裡？", "... 어디에요?"), ("洗手間", "화장실"), ("地鐵站", "지하철역")]
    },
    "泰國": {
        "👋 招呼": [("你好", "Sawasdee"), ("謝謝", "Khop khun"), ("對不起", "Kor tod")],
        "🍜 點餐": [("我要這個", "Ao an nee"), ("多少錢", "Tao rai?"), ("買單", "Check bin")],
        "🚆 交通": [("去...", "Bai ..."), ("廁所", "Hong nam"), ("這裡", "Tee nee")]
    }
}

# -------------------------------------
# 4. CSS 樣式 (美化版)
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
.stApp {{ background-color: {c_bg} !important; color: {c_text} !important; font-family: 'Inter', sans-serif !important; }}
[data-testid="stSidebarCollapsedControl"], footer {{ display: none !important; }}
header[data-testid="stHeader"] {{ height: 0 !important; background: transparent !important; }}

/* Live Card */
.live-card {{
    background: linear-gradient(145deg, {c_card}, {c_sec});
    border-left: 6px solid {c_primary}; border-radius: 16px;
    padding: 25px; margin-bottom: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.08);
}}
.live-title {{ font-size: 1.6rem; font-weight: 900; color: {c_text}; margin-bottom: 5px; }}
.live-meta {{ font-size: 0.95rem; color: {c_sub}; margin-top: 5px; }}

/* Apple Style Info Card (Flight) */
.flight-card {{
    background: {c_card}; border-radius: 16px; padding: 20px; margin-bottom: 15px;
    border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    position: relative; overflow: hidden;
}}
.flight-card::before {{
    content: ''; position: absolute; top: 0; left: 0; width: 6px; height: 100%;
    background: {c_primary};
}}
.flight-header {{ display: flex; justify-content: space-between; font-size: 0.9rem; color: {c_sub}; margin-bottom: 10px; }}
.flight-route {{ display: flex; align-items: center; justify-content: space-between; margin: 15px 0; }}
.flight-code {{ font-size: 2rem; font-weight: 900; color: {c_text}; }}
.flight-plane {{ font-size: 1.5rem; color: {c_primary}; }}

/* Hotel Card */
.hotel-card {{
    background: {c_card}; border-radius: 16px; overflow: hidden; margin-bottom: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);
}}
.hotel-img-placeholder {{
    height: 120px; background: linear-gradient(45deg, {c_sec}, {c_primary});
    display: flex; align-items: center; justify-content: center; font-size: 3rem; color: white;
}}
.hotel-body {{ padding: 15px; }}
.hotel-name {{ font-size: 1.2rem; font-weight: bold; margin-bottom: 5px; color: {c_text}; }}
.hotel-meta {{ font-size: 0.85rem; color: {c_sub}; display: flex; gap: 10px; align-items: center; }}
.hotel-badge {{ background: {c_sec}; color: {c_text}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}

/* Widget Card (Tools) */
.widget-card {{
    background: {c_card}; border-radius: 20px; padding: 20px; margin-bottom: 15px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.06); text-align: center;
    border: 1px solid rgba(0,0,0,0.03);
}}
.widget-icon {{ font-size: 2.5rem; margin-bottom: 10px; }}
.widget-value {{ font-size: 1.8rem; font-weight: 900; color: {c_primary}; }}
.widget-label {{ font-size: 0.9rem; color: {c_sub}; }}

/* SOS Card */
.sos-card {{
    background: #FF3B30; color: white; border-radius: 20px; padding: 25px;
    text-align: center; box-shadow: 0 10px 30px rgba(255, 59, 48, 0.3);
    cursor: pointer; transition: transform 0.1s;
}}
.sos-card:active {{ transform: scale(0.98); }}
.sos-title {{ font-size: 2rem; font-weight: 900; }}
.sos-sub {{ font-size: 1rem; opacity: 0.9; margin-bottom: 10px; }}

/* AI Box */
.ai-box {{ background: #F0F8FF; border: 1px solid #BEE3F8; border-radius: 12px; padding: 15px; color: #2C5282; }}

/* General Overrides */
div[data-testid="stRadio"] > div {{ background-color: {c_sec} !important; border-radius: 12px !important; }}
div[data-testid="stRadio"] label[data-checked="true"] {{ background-color: {c_card} !important; color: {c_text} !important; font-weight: bold !important; }}

/* Custom Apple Card for Itinerary */
.apple-card {{
    background: {c_card};
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid rgba(0,0,0,0.03);
    margin-bottom: 8px;
}}
.apple-title {{ font-weight: bold; font-size: 1rem; color: {c_text}; }}
.apple-loc {{ font-size: 0.85rem; color: {c_sub}; display: flex; align-items: center; margin-top: 4px; }}
.trans-card {{
    background: transparent;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px dashed {c_sec};
    color: {c_sub};
    font-size: 0.85rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.trans-tag {{
    background: {c_primary}; color: white; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin-left: 6px;
}}
</style>
"""
st.markdown(main_css, unsafe_allow_html=True)

# -------------------------------------
# 5. 主畫面
# -------------------------------------
st.markdown(f'<div style="font-size:2.2rem; font-weight:900; text-align:center; margin-bottom:5px; color:{c_text};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)

with st.expander("⚙️ 設定"):
    st.session_state.trip_title = st.text_input("標題", value=st.session_state.trip_title)
    st.session_state.show_ai_intro = st.toggle("🤖 顯示 AI 行程介紹", value=st.session_state.show_ai_intro)
    
    theme_name = st.selectbox("主題", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.selected_theme_name))
    if theme_name != st.session_state.selected_theme_name:
        st.session_state.selected_theme_name = theme_name
        st.rerun()
        
    c1, c2 = st.columns(2)
    st.session_state.start_date = c1.date_input("日期", value=st.session_state.start_date)
    st.session_state.trip_days_count = c2.number_input("天數", 1, 30, st.session_state.trip_days_count)
    
    prev_country = st.session_state.target_country
    country_options = list(DEFAULT_RATES.keys())
    try:
        idx = country_options.index(prev_country)
    except ValueError:
        idx = 0
    new_country = st.selectbox("地區", country_options, index=idx)
    
    if new_country != prev_country:
        st.session_state.target_country = new_country
        st.session_state.exchange_rate = DEFAULT_RATES[new_country]
        st.rerun()
    else:
        st.session_state.target_country = new_country

    st.session_state.exchange_rate = st.number_input(
        f"匯率 (1 {new_country}幣 換算 TWD)", 
        value=float(st.session_state.exchange_rate), 
        step=0.001, 
        format="%.4f"
    )
    
    uf = st.file_uploader("匯入 Excel", type=["xlsx"])
    if uf and st.button("匯入"): process_excel_upload(uf)

# Init Days
for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🚀 進行中", "📅 行程", "✨ 願望", "🎒 清單", "ℹ️ 資訊", "🧰 工具"])

# ==========================================
# 1. 🚀 進行中
# ==========================================
with tab1:
    all_steps = []
    for d in sorted(st.session_state.trip_data.keys()):
        day_items = sorted(st.session_state.trip_data[d], key=lambda x: x['time'])
        for item in day_items:
            info = item.copy()
            info['day_num'] = d
            all_steps.append(info)
    
    if st.session_state.current_step_index >= len(all_steps):
        st.balloons()
        st.success("🎉 恭喜！旅程已全部完成！")
        if st.button("🔄 重置進度"):
            st.session_state.current_step_index = 0
            st.session_state.ai_advice_cache = {}
            st.rerun()
    elif not all_steps:
        st.info("📭 請先到「📅 行程」分頁新增行程。")
    else:
        curr = all_steps[st.session_state.current_step_index]
        real_item = None
        for item in st.session_state.trip_data[curr['day_num']]:
            if item['id'] == curr['id']:
                real_item = item
                break
        
        prog = (st.session_state.current_step_index) / len(all_steps)
        st.progress(prog, text=f"旅程進度 {int(prog*100)}%")
        
        real_date = st.session_state.start_date + timedelta(days=curr['day_num'] - 1)
        date_str = real_date.strftime("%m/%d")
        
        st.markdown(f"""
        <div class="live-card">
            <div style="color:{c_primary}; font-weight:bold;">🔥 NOW - Day {curr['day_num']} ({date_str})</div>
            <div class="live-time">{curr['time']}</div>
            <div class="live-title">{curr['title']}</div>
            <div class="live-meta">📍 {curr['loc'] or '未設定'}</div>
            <div class="live-meta" style="margin-top:10px; background:rgba(255,255,255,0.5); padding:10px; border-radius:8px;">
                📝 {curr['note'] or '無備註'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("💰 快速記帳", expanded=False):
            if real_item:
                input_method = st.radio("方式", ["📸 拍照", "📂 上傳"], horizontal=True, key=f"live_in_{curr['id']}")
                uploaded_receipt = None
                if input_method == "📸 拍照":
                    if st.toggle("🔴 啟動相機", key=f"live_cam_tog_{curr['id']}"):
                        uploaded_receipt = st.camera_input("拍照", key=f"live_cam_{curr['id']}")
                else:
                    uploaded_receipt = st.file_uploader("上傳", type=["jpg","png"], key=f"live_upl_{curr['id']}")
                
                scan_flag = f"live_scan_{curr['id']}"
                if uploaded_receipt and not st.session_state.get(scan_flag, False):
                    with st.spinner("分析中..."):
                        results = analyze_receipt_image(uploaded_receipt)
                    if isinstance(results, list):
                        cnt = 0
                        for res in results:
                            if res.get('price', 0) > 0:
                                real_item['expenses'].append(res)
                                cnt += 1
                        if cnt > 0:
                            real_item['cost'] = sum(x['price'] for x in real_item['expenses'])
                            st.success(f"已加入 {cnt} 筆")
                            st.session_state[scan_flag] = True
                            time.sleep(1)
                            st.rerun()
                if not uploaded_receipt and st.session_state.get(scan_flag, False):
                    st.session_state[scan_flag] = False

                cx1, cx2, cx3 = st.columns([2, 1, 1])
                new_n = cx1.text_input("項目", key=f"live_n_{curr['id']}", label_visibility="collapsed")
                new_p = cx2.number_input("金額", min_value=0, key=f"live_p_{curr['id']}", label_visibility="collapsed")
                if cx3.button("➕", key=f"live_add_{curr['id']}"):
                    if new_n and new_p > 0:
                        real_item['expenses'].append({"name": new_n, "price": new_p})
                        real_item['cost'] = sum(x['price'] for x in real_item['expenses'])
                        st.rerun()

                if real_item.get('expenses'):
                    st.divider()
                    st.caption(f"已記錄花費 (總計 ¥{real_item['cost']:,})")
                    for ex in real_item['expenses']:
                        st.text(f"{ex['name']} : ¥{ex['price']:,}")

        if st.session_state.show_ai_intro:
            st.markdown("### ✨ AI 即時建議")
            item_id = curr['id']
            if item_id not in st.session_state.ai_advice_cache:
                with st.spinner("🤖 導遊正在分析..."):
                    resp = ""
                    ph = st.empty()
                    for chunk in get_ai_step_advice_stream(curr, st.session_state.target_country):
                        resp += chunk
                        ph.markdown(f"<div class='ai-box'>{resp}</div>", unsafe_allow_html=True)
                    st.session_state.ai_advice_cache[item_id] = resp
            else:
                st.markdown(f"<div class='ai-box'>{st.session_state.ai_advice_cache[item_id]}</div>", unsafe_allow_html=True)
                if st.button("🔄 重新生成"):
                    del st.session_state.ai_advice_cache[item_id]
                    st.rerun()

        st.markdown("---")
        c_back, c_next = st.columns([1, 2])
        if c_back.button("⬅️ 上一步"):
            if st.session_state.current_step_index > 0:
                st.session_state.current_step_index -= 1
                st.rerun()
        if c_next.button("✅ 完成，前往下一站 ➡️", type="primary", use_container_width=True):
            st.session_state.current_step_index += 1
            st.rerun()

# ==========================================
# 2. 行程規劃
# ==========================================
with tab2:
    selected_day_num = st.radio("DaySelect", list(range(1, st.session_state.trip_days_count + 1)), 
                                index=0, horizontal=True, label_visibility="collapsed", 
                                format_func=lambda x: f"Day {x}")
    
    current_date = st.session_state.start_date + timedelta(days=selected_day_num - 1)
    current_items = st.session_state.trip_data[selected_day_num]
    current_items.sort(key=lambda x: x['time'])
    
    all_cost = sum([item.get('cost', 0) for item in current_items])
    all_actual = sum([sum(x['price'] for x in item.get('expenses', [])) for item in current_items])
    
    c1, c2 = st.columns(2)
    c1.metric("預算", f"¥{all_cost:,}")
    c2.metric("支出", f"¥{all_actual:,}", delta=f"{all_cost - all_actual:,}" if all_actual > 0 else None)
    st.markdown("---")
    
    is_edit_mode = st.toggle("編輯模式")
    if is_edit_mode and st.button("➕ 新增行程", use_container_width=True):
        st.session_state.trip_data[selected_day_num].append({"id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": "", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30})
        st.rerun()

    for index, item in enumerate(current_items):
        map_link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(item['loc'])}" if item['loc'] else "#"
        map_btn = f'<a href="{map_link}" target="_blank" style="text-decoration:none; margin-left:8px; font-size:0.8rem; background:{c_sec}; color:{c_text}; padding:2px 8px; border-radius:10px; opacity:0.8;">🗺️</a>' if item['loc'] else ""
        cost_display = f'<div style="background:{c_primary}; color:white; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:bold; white-space:nowrap;">¥{sum(x["price"] for x in item.get("expenses", [])):,}</div>' if item.get('expenses') else ""
        
        st.markdown(f"""<div style="display:flex; gap:15px; margin-bottom:0px;"><div style="display:flex; flex-direction:column; align-items:center; width:50px;"><div style="font-weight:700; color:{c_text}; font-size:1.1rem;">{item['time']}</div><div style="flex-grow:1; width:2px; background:{c_sec}; margin:5px 0; opacity:0.3; border-radius:2px;"></div></div><div style="flex-grow:1;"><div class="apple-card" style="margin-bottom:0px;"><div style="display:flex; justify-content:space-between; align-items:flex-start;"><div class="apple-title" style="margin-top:0;">{item['title']}</div>{cost_display}</div><div class="apple-loc">📍 {item['loc'] or '未設定'} {map_btn}</div><div style="font-size:0.85rem; color:{c_sub}; background:{c_bg}; padding:8px; border-radius:8px; margin-top:8px; line-height:1.4;">📝 {item['note']}</div></div></div></div>""", unsafe_allow_html=True)
        
        if item.get('expenses'):
            total_ex = sum(x['price'] for x in item['expenses'])
            with st.expander(f"🧾 明細 (¥{total_ex:,})", expanded=False):
                for exp in item['expenses']:
                    st.markdown(f"- {exp['name']}: ¥{exp['price']:,}")

        if is_edit_mode:
            with st.expander("✏️ 編輯", expanded=False):
                c1, c2 = st.columns([2, 1])
                item['title'] = c1.text_input("名稱", item['title'], key=f"t_{item['id']}")
                item['time'] = c2.time_input("時間", datetime.strptime(item['time'], "%H:%M").time(), key=f"tm_{item['id']}").strftime("%H:%M")
                item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                if st.button("🗑️ 刪除", key=f"del_{item['id']}"):
                    st.session_state.trip_data[selected_day_num].pop(index)
                    st.rerun()
        
        if index < len(current_items) - 1:
            next_item = current_items[index+1]
            nav_link = generate_google_nav_link(item['loc'], next_item['loc'])
            t_mode = item.get('trans_mode', '📍 移動')
            st.markdown(f"""<div style="display:flex; gap:15px;"><div style="display:flex; flex-direction:column; align-items:center; width:50px;"><div style="flex-grow:1; width:2px; border-left:2px dashed {c_sec}; margin:0; opacity:0.6;"></div></div><div style="flex-grow:1; padding:5px 0;"><div class="trans-card"><div style="display:flex; flex-direction:column;"><div style="font-size:0.7rem; color:#888; margin-bottom:2px;">推薦路線 (RECOMMENDED)</div><div style="display:flex; align-items:center; gap:8px;"><div style="font-weight:bold; font-size:0.9rem;">{t_mode}</div><div class="trans-tag">最快速</div></div></div><div style="text-align:right;"><div style="font-weight:bold; font-size:0.9rem;">{item.get('trans_min', 30)} min</div><a href="{nav_link}" target="_blank" style="text-decoration:none; font-size:0.75rem; color:#007AFF;">➤ 導航</a></div></div></div></div>""", unsafe_allow_html=True)

# ==========================================
# 3. 願望清單
# ==========================================
with tab3:
    col_wish_1, col_wish_2 = st.columns([2, 1])
    col_wish_1.subheader("✨ 願望清單")
    
    with col_wish_2.popover("⚡ 智能貼上"):
        st.markdown("複製 Google Maps 連結或 Tabelog/網誌文字，AI 自動分析！")
        raw_text = st.text_area("貼上文字...", height=100)
        if st.button("🪄 AI 解析加入"):
            with st.spinner("AI 正在閱讀中..."):
                res = parse_wishlist_text(raw_text)
                if res and 'title' in res:
                    st.session_state.wishlist.append({
                        "id": int(time.time()), 
                        "title": res.get('title', '未命名'), 
                        "loc": res.get('loc', ''), 
                        "note": res.get('note', '')
                    })
                    st.success("成功加入！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("解析失敗，請重試")

    with st.expander("➕ 手動新增", expanded=False):
        w_title = st.text_input("名稱")
        w_loc = st.text_input("地點")
        w_note = st.text_input("備註")
        if st.button("加入") and w_title:
            st.session_state.wishlist.append({"id": int(time.time()), "title": w_title, "loc": w_loc, "note": w_note})
            st.rerun()

    for i, wish in enumerate(st.session_state.wishlist):
        with st.container():
            st.markdown(f"""<div class="apple-card" style="padding:15px; margin-bottom:10px; border-left:4px solid {c_primary};"><div style="font-weight:bold; font-size:1.1rem;">{wish['title']}</div><div style="font-size:0.9rem; color:{c_sub};">📍 {wish['loc']}｜📝 {wish['note']}</div></div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 1, 1])
            target_day = c1.selectbox("移至", list(range(1, st.session_state.trip_days_count + 1)), key=f"wd_{wish['id']}")
            if c2.button("排程", key=f"wm_{wish['id']}"):
                new_item = {"id": int(time.time()), "time": "09:00", "title": wish['title'], "loc": wish['loc'], "cost": 0, "cat": "spot", "note": wish['note'], "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
                st.session_state.trip_data[target_day].append(new_item)
                st.session_state.wishlist.pop(i)
                st.rerun()
            if c3.button("刪", key=f"wdl_{wish['id']}"):
                st.session_state.wishlist.pop(i)
                st.rerun()

# ==========================================
# 4. 準備清單 (可編輯版)
# ==========================================
with tab4:
    col_check_1, col_check_2 = st.columns([4, 1])
    col_check_1.subheader("🎒 準備清單")
    # [Fix] Added key to prevent duplicate ID error
    is_check_edit = col_check_2.toggle("✏️ 編輯", key="toggle_check_edit")

    if is_check_edit:
        new_cat = st.text_input("➕ 新增分類名稱")
        if st.button("新增分類") and new_cat:
            if new_cat not in st.session_state.checklist:
                st.session_state.checklist[new_cat] = {}
                st.rerun()
        
        st.divider()

    categories = list(st.session_state.checklist.keys())
    
    for category in categories:
        items = st.session_state.checklist[category]
        
        if is_check_edit:
            c_head_1, c_head_2 = st.columns([4, 1])
            c_head_1.markdown(f"**📂 {category}**")
            if c_head_2.button("🗑️", key=f"del_cat_{category}"):
                del st.session_state.checklist[category]
                st.rerun()
                
            new_item_txt = st.text_input(f"在「{category}」新增項目", key=f"new_item_{category}")
            if st.button("加入項目", key=f"add_btn_{category}") and new_item_txt:
                st.session_state.checklist[category][new_item_txt] = False
                st.rerun()

            item_keys = list(items.keys())
            for item in item_keys:
                c_i_1, c_i_2 = st.columns([4, 1])
                c_i_1.text(f" - {item}")
                if c_i_2.button("❌", key=f"del_i_{category}_{item}"):
                    del st.session_state.checklist[category][item]
                    st.rerun()
            st.divider()
            
        else:
            st.markdown(f"**{category}**")
            cols = st.columns(2)
            for i, (item, checked) in enumerate(items.items()):
                st.session_state.checklist[category][item] = cols[i % 2].checkbox(item, value=checked)

# ==========================================
# 5. 資訊 (可編輯版)
# ==========================================
with tab5:
    col_info_head, col_info_edit = st.columns([4, 1])
    col_info_head.subheader("✈️ 航班")
    
    # [Fix] Added key to prevent duplicate ID error
    is_info_edit = col_info_edit.toggle("✏️ 編輯", key="toggle_info_edit")
    
    flights = st.session_state.flight_info
    f_out = flights['outbound']
    f_in = flights['inbound']
    
    if is_info_edit:
        st.markdown("**去程 (Outbound)**")
        c1, c2, c3 = st.columns(3)
        f_out['date'] = c1.text_input("日期", f_out['date'], key="fd_out")
        f_out['code'] = c2.text_input("班號", f_out['code'], key="fc_out")
        c1, c2 = st.columns(2)
        f_out['dep'] = c1.text_input("起飛時間", f_out['dep'], key="ft_d_out")
        f_out['arr'] = c2.text_input("抵達時間", f_out['arr'], key="ft_a_out")
        f_out['dep_loc'] = c1.text_input("起飛地", f_out['dep_loc'], key="fl_d_out")
        f_out['arr_loc'] = c2.text_input("抵達地", f_out['arr_loc'], key="fl_a_out")
        
        st.divider()
        st.markdown("**回程 (Inbound)**")
        c1, c2, c3 = st.columns(3)
        f_in['date'] = c1.text_input("日期", f_in['date'], key="fd_in")
        f_in['code'] = c2.text_input("班號", f_in['code'], key="fc_in")
        c1, c2 = st.columns(2)
        f_in['dep'] = c1.text_input("起飛時間", f_in['dep'], key="ft_d_in")
        f_in['arr'] = c2.text_input("抵達時間", f_in['arr'], key="ft_a_in")
        f_in['dep_loc'] = c1.text_input("起飛地", f_in['dep_loc'], key="fl_d_in")
        f_in['arr_loc'] = c2.text_input("抵達地", f_in['arr_loc'], key="fl_a_in")
    else:
        st.markdown(f"""
        <div class="flight-card">
            <div class="flight-header"><span>DEPARTURE</span><span>{f_out['date']}</span></div>
            <div class="flight-route">
                <div class="flight-code">{f_out['dep_loc']}</div>
                <div class="flight-plane">✈</div>
                <div class="flight-code">{f_out['arr_loc']}</div>
            </div>
            <div style="display:flex; justify-content:space-between; font-weight:bold;">
                <div>{f_out['dep']}</div>
                <div>{f_out['code']}</div>
                <div>{f_out['arr']}</div>
            </div>
        </div>
        <div class="flight-card">
            <div class="flight-header"><span>RETURN</span><span>{f_in['date']}</span></div>
            <div class="flight-route">
                <div class="flight-code">{f_in['dep_loc']}</div>
                <div class="flight-plane">✈</div>
                <div class="flight-code">{f_in['arr_loc']}</div>
            </div>
            <div style="display:flex; justify-content:space-between; font-weight:bold;">
                <div>{f_in['dep']}</div>
                <div>{f_in['code']}</div>
                <div>{f_in['arr']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    st.subheader("🏨 住宿")
    if is_info_edit:
        if st.button("➕ 新增飯店"):
            new_id = len(st.session_state.hotel_info) + 1
            st.session_state.hotel_info.append({"id": new_id, "name": "新飯店", "range": "", "date": "", "addr": "", "link": ""})
            st.rerun()
            
        for i, hotel in enumerate(st.session_state.hotel_info):
            with st.expander(f"編輯: {hotel['name']}", expanded=True):
                hotel['name'] = st.text_input("名稱", hotel['name'], key=f"hn_{i}")
                c1, c2 = st.columns(2)
                hotel['range'] = c1.text_input("天數(e.g. D1-D3)", hotel['range'], key=f"hr_{i}")
                hotel['date'] = c2.text_input("日期", hotel['date'], key=f"hd_{i}")
                hotel['addr'] = st.text_input("地址", hotel['addr'], key=f"ha_{i}")
                if st.button("🗑️ 刪除", key=f"hdel_{i}"):
                    st.session_state.hotel_info.pop(i)
                    st.rerun()
    else:
        for hotel in st.session_state.hotel_info:
            st.markdown(f"""
            <div class="hotel-card">
                <div class="hotel-img-placeholder">🏨</div>
                <div class="hotel-body">
                    <div class="hotel-name">{hotel['name']}</div>
                    <div class="hotel-meta">
                        <span class="hotel-badge">{hotel['range']}</span>
                        <span>{hotel['date']}</span>
                    </div>
                    <div class="hotel-meta" style="margin-top:8px;">📍 {hotel['addr']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 6. 工具
# ==========================================
with tab6:
    st.header("🧰 實用工具")
    
    st.subheader("💴 匯率計算")
    col_calc1, col_calc2 = st.columns(2)
    amt = col_calc1.number_input("外幣", value=1000, step=100)
    twd = int(amt * st.session_state.exchange_rate)
    
    st.markdown(f"""
    <div class="widget-card">
        <div class="widget-label">約合台幣</div>
        <div class="widget-value">NT$ {twd:,}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if amt > 0:
        tax_free = int(amt / 1.1)
        refund = amt - tax_free
        st.caption(f"🛍️ 免稅價約: {tax_free:,} | 退稅額約: {refund:,}")

    st.divider()
    
    st.subheader("🗣️ 旅遊實用會話")
    target_c = st.session_state.target_country
    
    if target_c in SURVIVAL_PHRASES:
        phrases = SURVIVAL_PHRASES[target_c]
        tabs = st.tabs(list(phrases.keys()))
        for i, (category, items) in enumerate(phrases.items()):
            with tabs[i]:
                for zh, local in items:
                    st.markdown(f"""
                    <div style="background:{c_bg}; border:1px solid {c_sec}; padding:12px; border-radius:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:bold; color:{c_text};">{zh}</span>
                        <span style="color:{c_primary}; font-weight:bold; font-size:1.1rem;">{local}</span>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("目前僅支援 日/韓/泰 地區的會話")

    st.divider()
    
    st.subheader("🛍️ 購物清單")
    edited_df = st.data_editor(st.session_state.shopping_list, num_rows="dynamic", key="shop_edit", use_container_width=True)
    if not edited_df.equals(st.session_state.shopping_list):
        st.session_state.shopping_list = edited_df
        st.rerun()

    st.divider()
    
    st.subheader("🆘 緊急求助")
    target_country_sos = st.session_state.target_country
    sos_map = {
        "日本": {"迷路": "迷子になりました", "過敏": "アレルギーがあります", "醫院": "病院に連れて行って"},
        "韓國": {"迷路": "길을 잃었어요", "過敏": "알레르기가 있어요", "醫院": "병원으로 가주세요"},
        "泰國": {"迷路": "Long tang", "過敏": "Pae a-han", "醫院": "Bai rong paya ban"}
    }
    
    if target_country_sos in sos_map:
        s_type = st.selectbox("選擇緊急狀況", list(sos_map[target_country_sos].keys()))
        s_txt = sos_map[target_country_sos][s_type]
        st.markdown(f"""
        <div class="sos-card">
            <div class="sos-sub">請向當地人出示此畫面</div>
            <div class="sos-title">{s_txt}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("目前僅支援 日/韓/泰")
        
    st.divider()
    
    st.subheader("☁️ 雲端同步")
    c1, c2 = st.columns(2)
    if c1.button("☁️ 上傳"):
        if CLOUD_AVAILABLE:
            data = {"trip": st.session_state.trip_data, "wish": st.session_state.wishlist, "check": st.session_state.checklist}
            res = save_to_cloud(json.dumps(data, default=str))
            st.toast(res[1] if res[0] else f"錯誤: {res[1]}")
        else: st.error("缺少雲端套件 (gspread)")
    if c2.button("📥 下載"):
        if CLOUD_AVAILABLE:
            raw = load_from_cloud()
            if raw:
                d = json.loads(raw)
                if "trip" in d: st.session_state.trip_data = {int(k):v for k,v in d['trip'].items()}
                st.toast("成功")
                time.sleep(1)
                st.rerun()
        else: st.error("缺少雲端套件 (gspread)")
