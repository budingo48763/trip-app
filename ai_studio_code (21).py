import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
import random
import json

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

# --- 地理編碼 (地址轉經緯度) ---
@st.cache_data
def get_lat_lon(location_name):
    """使用 OSM 免費服務將地名轉為經緯度 (有快取避免被鎖)"""
    if not MAP_AVAILABLE: return None
    try:
        geolocator = Nominatim(user_agent="my_trip_app_demo_v1")
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

# --- 天氣服務 ---
class WeatherService:
    WEATHER_ICONS = {"Sunny": "☀️", "Cloudy": "☁️", "Rainy": "🌧️", "Snowy": "❄️"}
    @staticmethod
    def get_forecast(location, date_obj):
        random.seed(f"{location}{date_obj.strftime('%Y%m%d')}")
        base_temp = 20 if date_obj.month not in [12,1,2] else 5
        high = base_temp + random.randint(0, 5)
        low = base_temp - random.randint(3, 8)
        cond = random.choice(["Sunny", "Cloudy", "Rainy"])
        return {"high": high, "low": low, "icon": WeatherService.WEATHER_ICONS[cond], "desc": cond}

def get_packing_recommendations(trip_data, start_date):
    recommendations = set()
    has_rain = False
    min_temp = 100
    for day, items in trip_data.items():
        loc = items[0]['loc'] if items else "City"
        w = WeatherService.get_forecast(loc, start_date + timedelta(days=day-1))
        if w['desc'] in ["Rainy", "Snowy"]: has_rain = True
        min_temp = min(min_temp, w['low'])
    if has_rain: recommendations.add("☔ 折疊傘/雨衣")
    if min_temp < 15: recommendations.add("🧥 保暖外套")
    else: recommendations.add("🧢 帽子/防曬")
    return list(recommendations)

def get_single_map_link(location):
    if not location: return "#"
    if location.startswith("http"): return location
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(location)}"

def generate_google_nav_link(origin, dest, mode="transit"):
    """產生 A點到 B點的 Google Maps 導航連結"""
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
                "id": int(time.time()*1000)+_, "time": str(row['Time']), "title": str(row['Title']),
                "loc": str(row.get('Location','')), "cost": int(row.get('Cost',0)), 
                "note": str(row.get('Note','')), "expenses": []
            })
        st.session_state.trip_data = new_trip_data
        st.session_state.trip_days_count = max(new_trip_data.keys())
        st.rerun()
    except:
        st.error("格式錯誤")

# -------------------------------------
# 3. 初始化 & 資料
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 東京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "target_country" not in st.session_state: st.session_state.target_country = "日本"
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "⛩️ 京都緋紅 (預設)"
if "start_date" not in st.session_state: st.session_state.start_date = datetime(2026, 1, 17)
if "wishlist" not in st.session_state: st.session_state.wishlist = []
if "shopping_list" not in st.session_state: st.session_state.shopping_list = pd.DataFrame(columns=["對象", "商品名稱", "預算", "已購買"])

current_theme = THEMES[st.session_state.selected_theme_name]

# 預設資料
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "time": "10:00", "title": "抵達機場", "loc": "成田機場", "cost": 0, "note": "領取周遊券", "expenses": [], "trans_mode": "🚆 Skyliner", "trans_min": 45},
            {"id": 102, "time": "12:00", "title": "飯店 Check-in", "loc": "上野站", "cost": 0, "note": "寄放行李", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 10},
            {"id": 103, "time": "13:00", "title": "阿美橫町", "loc": "阿美橫町", "cost": 2000, "note": "吃海鮮丼", "expenses": [], "trans_mode": "🚆 山手線", "trans_min": 20},
            {"id": 104, "time": "16:00", "title": "淺草寺", "loc": "淺草雷門", "cost": 500, "note": "拍照、抽籤", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
        ]
    }
    # 補齊天數
    for d in range(2, 6): st.session_state.trip_data[d] = []

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {"outbound": {"date": "1/17", "code": "JX800", "dep":"10:00", "arr":"14:00", "dep_loc":"TPE", "arr_loc":"NRT"}, "inbound": {"date": "1/21", "code": "JX801", "dep":"15:00", "arr":"18:00", "dep_loc":"NRT", "arr_loc":"TPE"}}

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [{"id": 1, "name": "APA Hotel Ueno", "range": "D1-D4", "date": "1/17-1/21", "addr": "上野...", "link": ""}]

if "checklist" not in st.session_state:
    st.session_state.checklist = {"證件": {"護照":False}, "電子": {"網卡":False}, "衣物": {"外套":False}}

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船", "✈️ 飛機"]

# -------------------------------------
# 4. CSS 樣式 (Apple Style + Map)
# -------------------------------------
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp {{ background-color: {current_theme['bg']} !important; color: {current_theme['text']} !important; font-family: 'Inter', sans-serif !important; }}
    [data-testid="stSidebarCollapsedControl"], footer {{ display: none !important; }}
    header[data-testid="stHeader"] {{ height: 0 !important; background: transparent !important; }}

    /* 卡片樣式 */
    .apple-card {{
        background: rgba(255, 255, 255, 0.95);
        border-radius: 16px; padding: 18px; margin-bottom: 0px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); border: 1px solid rgba(0,0,0,0.05);
    }}
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
    
    /* 天氣 Widget */
    .weather-widget {{
        background: linear-gradient(135deg, {current_theme['primary']} 0%, {current_theme['text']} 150%);
        color: white; padding: 20px; border-radius: 24px; margin-bottom: 25px;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }}

    /* Day 按鈕 */
    div[data-testid="stRadio"] > div {{ gap: 5px; overflow-x: auto; flex-wrap: nowrap; }}
    div[data-testid="stRadio"] label {{
        background: white; border: 1px solid #EEE; border-radius: 10px;
        padding: 8px 16px; min-width: 60px; text-align: center;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] {{
        background: {current_theme['text']}; color: white; border-color: {current_theme['text']};
    }}
    
    /* 輸入框優化 */
    input {{ background: transparent !important; }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 5. 主畫面
# -------------------------------------
st.markdown(f'<div style="font-size:2rem; font-weight:900; text-align:center; margin-bottom:5px;">{st.session_state.trip_title}</div>', unsafe_allow_html=True)

# Tabs 定義
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📅 行程", "🗺️ 地圖", "✨ 願望", "🎒 清單", "ℹ️ 資訊", "🧰 工具"])

# ==========================================
# Tab 1: 行程規劃 (含交通卡片 & 記帳掃描)
# ==========================================
with tab1:
    selected_day_num = st.radio("Day", list(range(1, st.session_state.trip_days_count + 1)), horizontal=True, label_visibility="collapsed", format_func=lambda x: f"D{x}")
    current_date = st.session_state.start_date + timedelta(days=selected_day_num - 1)
    items = st.session_state.trip_data[selected_day_num]
    items.sort(key=lambda x: x['time'])

    # 天氣卡片
    loc_name = items[0]['loc'] if items else "City"
    w = WeatherService.get_forecast(loc_name, current_date)
    st.markdown(f"""
    <div class="weather-widget">
        <div>
            <div style="font-size:2.5rem;">{w['icon']}</div>
            <div style="font-size:1.5rem; font-weight:bold;">{w['high']}°C</div>
        </div>
        <div style="text-align:right;">
            <div style="font-weight:bold; opacity:0.9;">{current_date.strftime('%m/%d %a')}</div>
            <div style="opacity:0.8;">📍 {loc_name}</div>
            <div style="font-size:0.9rem;">{w['desc']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    is_edit = st.toggle("✏️ 編輯模式")
    if is_edit and st.button("➕ 新增行程", use_container_width=True):
        items.append({"id": int(time.time()*1000), "time": "10:00", "title": "新行程", "loc": "", "cost": 0, "note": "", "expenses": []})
        st.rerun()

    for i, item in enumerate(items):
        # 卡片內容
        cost_html = f'<span style="background:{current_theme["primary"]}; color:white; padding:2px 8px; border-radius:10px; font-size:0.7rem;">¥{item["cost"]:,}</span>' if item['cost'] > 0 else ""
        map_link = get_single_map_link(item['loc'])
        map_icon = f'<a href="{map_link}" target="_blank" style="text-decoration:none; margin-left:5px;">🗺️</a>' if item['loc'] else ""
        
        # 記帳明細
        exp_html = ""
        if item.get("expenses"):
            exp_rows = "".join([f"<div style='display:flex; justify-content:space-between; font-size:0.8rem; color:#666;'><span>{e['name']}</span><span>¥{e['price']:,}</span></div>" for e in item['expenses']])
            exp_html = f"<div style='margin-top:8px; padding-top:5px; border-top:1px dashed #EEE;'>{exp_rows}</div>"

        # 行程卡片 HTML
        st.markdown(f"""
        <div style="display:flex; gap:15px;">
            <div style="display:flex; flex-direction:column; align-items:center; width:50px;">
                <div style="font-weight:bold; color:{current_theme['text']}; font-size:1rem;">{item['time']}</div>
                <div style="flex-grow:1; width:2px; background:#EEE; margin:5px 0;"></div>
            </div>
            <div style="flex-grow:1;">
                <div class="apple-card">
                    <div style="display:flex; justify-content:space-between;">
                        <div style="font-weight:bold; font-size:1.1rem;">{item['title']}</div>
                        {cost_html}
                    </div>
                    <div style="font-size:0.9rem; color:#666; margin-top:2px;">📍 {item['loc'] or '未設定'} {map_icon}</div>
                    <div style="font-size:0.85rem; color:#888; margin-top:5px;">{item['note']}</div>
                    {exp_html}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 編輯區塊 (含掃描)
        if is_edit:
            with st.container(border=True):
                c1, c2 = st.columns([1, 1])
                item['title'] = c1.text_input("名稱", item['title'], key=f"t_{item['id']}")
                item['time'] = c2.text_input("時間", item['time'], key=f"tm_{item['id']}")
                item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                
                st.markdown("**💰 記帳**")
                # --- 📷 掃描收據 (模擬功能) ---
                scan_col, manual_col = st.columns([1, 2])
                with scan_col:
                    uploaded_receipt = st.file_uploader("📷 掃描收據", type=["jpg", "png"], key=f"scan_{item['id']}", label_visibility="collapsed")
                    if uploaded_receipt:
                        # 模擬 AI 辨識結果
                        st.success("辨識成功！(模擬)")
                        # 自動填入 (透過 session state 傳遞)
                        if f"new_exp_n_{item['id']}" not in st.session_state:
                            st.session_state[f"new_exp_n_{item['id']}"] = "午餐定食 (掃描)"
                            st.session_state[f"new_exp_p_{item['id']}"] = 1280
                
                # 手動輸入 (會自動被掃描結果填入)
                e_name = st.text_input("項目", key=f"new_exp_n_{item['id']}", placeholder="項目")
                e_price = st.number_input("金額", min_value=0, key=f"new_exp_p_{item['id']}")
                if st.button("➕ 加入", key=f"add_{item['id']}"):
                    if e_name: 
                        item['expenses'].append({"name": e_name, "price": e_price})
                        item['cost'] = sum(x['price'] for x in item['expenses'])
                        # 清空
                        del st.session_state[f"new_exp_n_{item['id']}"]
                        del st.session_state[f"new_exp_p_{item['id']}"]
                        st.rerun()
                
                if st.button("🗑️ 刪除行程", key=f"del_{item['id']}"):
                    items.pop(i)
                    st.rerun()

        # --- 推薦路線卡片 (圖片1 效果) ---
        if i < len(items) - 1:
            next_item = items[i+1]
            tm = item.get('trans_mode', '移動')
            tmin = item.get('trans_min', 30)
            
            # 生成真實 Google Maps 導航連結
            nav_link = generate_google_nav_link(item['loc'], next_item['loc'])
            
            # 推薦路線 HTML
            st.markdown(f"""
            <div class="trans-card">
                <div style="display:flex; flex-direction:column;">
                    <div style="font-size:0.8rem; color:#888; margin-bottom:2px;">推薦路線 (RECOMMENDED)</div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="font-weight:bold; font-size:0.95rem;">{tm}</div>
                        <div class="trans-tag">最快速</div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-weight:bold; font-size:0.95rem;">{tmin} min</div>
                    <a href="{nav_link}" target="_blank" style="text-decoration:none; font-size:0.8rem; color:#007AFF;">➤ 導航</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if is_edit:
                c_tm1, c_tm2 = st.columns(2)
                item['trans_mode'] = c_tm1.selectbox("方式", TRANSPORT_OPTIONS, key=f"trm_{item['id']}")
                item['trans_min'] = c_tm2.number_input("分鐘", value=tmin, step=5, key=f"tmn_{item['id']}")

# ==========================================
# Tab 2: 地圖軌跡 (Leaflet + OSM)
# ==========================================
with tab2:
    st.subheader(f"🗺️ Day {selected_day_num} 路線圖")
    
    if MAP_AVAILABLE:
        # 準備地圖資料
        map_items = [it for it in items if it['loc']]
        if map_items:
            # 取得第一個點的座標作為中心
            start_coords = get_lat_lon(map_items[0]['loc'])
            if not start_coords: start_coords = [35.6895, 139.6917] # 東京預設
            
            m = folium.Map(location=start_coords, zoom_start=13)
            
            route_points = []
            for idx, item in enumerate(map_items):
                coords = get_lat_lon(item['loc'])
                if coords:
                    route_points.append(coords)
                    # 加上數字標記
                    folium.Marker(
                        coords, 
                        popup=item['title'],
                        icon=folium.Icon(color='red', icon=str(idx+1), prefix='fa')
                    ).add_to(m)
            
            # 畫線連接 (圖片2 效果)
            if len(route_points) > 1:
                folium.PolyLine(
                    route_points,
                    color="#007AFF",
                    weight=5,
                    opacity=0.8
                ).add_to(m)
            
            st_folium(m, width="100%", height=400)
        else:
            st.info("本行程尚無地點資訊，無法繪製地圖。")
    else:
        st.error("請安裝 folium 與 streamlit-folium 套件以顯示地圖。")

# ==========================================
# Tab 3: 願望清單
# ==========================================
with tab3:
    st.subheader("✨ 願望清單")
    with st.expander("➕ 新增", expanded=False):
        t = st.text_input("名稱")
        l = st.text_input("地點")
        if st.button("加入") and t:
            st.session_state.wishlist.append({"id": int(time.time()), "title": t, "loc": l, "note": ""})
            st.rerun()
            
    for i, wish in enumerate(st.session_state.wishlist):
        with st.container(border=True):
            st.markdown(f"**{wish['title']}** (📍 {wish['loc']})")
            c1, c2 = st.columns([1, 1])
            target_d = c1.selectbox("移至", list(range(1, st.session_state.trip_days_count+1)), key=f"wd_{wish['id']}")
            if c2.button("排入行程", key=f"wm_{wish['id']}"):
                new_item = {"id": int(time.time()), "time": "09:00", "title": wish['title'], "loc": wish['loc'], "cost": 0, "note": "", "expenses": []}
                st.session_state.trip_data[target_d].append(new_item)
                st.session_state.wishlist.pop(i)
                st.toast(f"已排入 Day {target_d}")
                time.sleep(1)
                st.rerun()

# ==========================================
# Tab 4: 準備清單 (同前)
# ==========================================
with tab4:
    recs = get_packing_recommendations(st.session_state.trip_data, st.session_state.start_date)
    st.info(f"☁️ 根據天氣建議攜帶：{', '.join(recs)}")
    for cat, items_dict in st.session_state.checklist.items():
        st.markdown(f"**{cat}**")
        cols = st.columns(2)
        for idx, (k, v) in enumerate(items_dict.items()):
            st.session_state.checklist[cat][k] = cols[idx%2].checkbox(k, value=v)

# ==========================================
# Tab 5: 資訊 (同前)
# ==========================================
with tab5:
    st.subheader("✈️ 航班")
    f = st.session_state.flight_info
    st.markdown(f"<div class='apple-card'>🛫 去程 {f['outbound']['date']} {f['outbound']['code']}<br>🛬 回程 {f['inbound']['date']} {f['inbound']['code']}</div>", unsafe_allow_html=True)
    
    st.divider()
    st.subheader("🏨 住宿")
    for h in st.session_state.hotel_info:
        st.markdown(f"<div class='apple-card'><b>{h['name']}</b><br>{h['range']}</div>", unsafe_allow_html=True)

# ==========================================
# Tab 6: 工具 (雲端/匯率)
# ==========================================
with tab6:
    st.subheader("☁️ 雲端同步")
    c1, c2 = st.columns(2)
    if c1.button("☁️ 上傳"):
        if CLOUD_AVAILABLE:
            data = {
                "trip": st.session_state.trip_data,
                "wish": st.session_state.wishlist,
                "check": st.session_state.checklist
            }
            res = save_to_cloud(json.dumps(data, default=str))
            st.toast(res[1] if res[0] else f"錯誤: {res[1]}")
        else: st.error("缺少雲端套件")
        
    if c2.button("📥 下載"):
        if CLOUD_AVAILABLE:
            raw = load_from_cloud()
            if raw:
                d = json.loads(raw)
                if "trip" in d: st.session_state.trip_data = {int(k):v for k,v in d['trip'].items()}
                if "wish" in d: st.session_state.wishlist = d['wish']
                st.toast("同步成功")
                time.sleep(1)
                st.rerun()
        else: st.error("缺少雲端套件")
        
    st.divider()
    st.subheader("💴 匯率換算")
    amt = st.number_input("外幣", step=100)
    st.metric("台幣", int(amt * st.session_state.exchange_rate))
