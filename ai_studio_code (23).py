import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
from PIL import Image
import io

# 嘗試匯入圖片裁剪工具
try:
    from streamlit_cropper import st_cropper
    HAS_CROPPER = True
except ImportError:
    HAS_CROPPER = False

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="2026 旅程規劃", page_icon="✈️", layout="centered", initial_sidebar_state="collapsed")

# -------------------------------------
# 2. 主題與資料庫
# -------------------------------------

# 🎨 主題配色庫
THEMES = {
    "京都緋紅": {
        "bg": "#FDFCF5", "card": "#FFFFFF", "text": "#2B2B2B", "primary": "#8E2F2F", "secondary": "#D6A6A6", "sub": "#666666",
        "cover": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=2070&auto=format&fit=crop"
    },
    "宇治抹茶": {
        "bg": "#F7FAF5", "card": "#FFFFFF", "text": "#1C3318", "primary": "#557C55", "secondary": "#C6EBC5", "sub": "#405D40",
        "cover": "https://images.unsplash.com/photo-1624253321171-1be53e12f5f4?q=80&w=1974&auto=format&fit=crop"
    },
    "莫蘭迪藍": {
        "bg": "#F0F4F8", "card": "#FFFFFF", "text": "#243B53", "primary": "#486581", "secondary": "#BCCCDC", "sub": "#627D98",
        "cover": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=2073&auto=format&fit=crop"
    },
    "焦糖奶茶": {
        "bg": "#FAF6F1", "card": "#FFFFFF", "text": "#4A3B32", "primary": "#9C7C64", "secondary": "#E0D0C5", "sub": "#7D6556",
        "cover": "https://images.unsplash.com/photo-1469334031218-e382a71b716b?q=80&w=2070&auto=format&fit=crop"
    },
    "江戶紫鳶": {
        "bg": "#F8F5FA", "card": "#FFFFFF", "text": "#2D2436", "primary": "#6B4C75", "secondary": "#D6BCFA", "sub": "#553C9A",
        "cover": "https://images.unsplash.com/photo-1492571350019-22de08371fd3?q=80&w=1953&auto=format&fit=crop"
    },
    "現代極簡": {
        "bg": "#F5F5F5", "card": "#FFFFFF", "text": "#1A1A1A", "primary": "#4A4A4A", "secondary": "#CCCCCC", "sub": "#666666",
        "cover": "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?q=80&w=2070&auto=format&fit=crop"
    }
}

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船", "✈️ 飛機"]

# -------------------------------------
# 3. 核心邏輯函數
# -------------------------------------

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
# 4. 初始化 & 資料 (恢復完整行程)
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "target_country" not in st.session_state: st.session_state.target_country = "日本"
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "京都緋紅"
if "custom_cover_img" not in st.session_state: st.session_state.custom_cover_img = None
if "show_theme_modal" not in st.session_state: st.session_state.show_theme_modal = False

current_theme = THEMES[st.session_state.selected_theme_name]

# 完整 5 天行程資料恢復
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

# 確保每個 Day 都有資料
for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

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
# 5. CSS 樣式 (強力修復 Day 版型)
# -------------------------------------
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp {{ background-color: {current_theme['bg']} !important; color: {current_theme['text']} !important; font-family: 'Noto Serif JP', serif !important; }}
    [data-testid="stSidebarCollapsedControl"], footer, header {{ display: none !important; }}
    
    /* --- Day 按鈕 (強制修正版) --- */
    div[role="radiogroup"] {{
        display: flex !important; flex-direction: row !important; overflow-x: auto !important;
        gap: 10px !important; padding-bottom: 5px !important; width: 100% !important;
    }}
    div[role="radiogroup"] label {{
        background: {current_theme['card']} !important; border: 1px solid #E0E0E0 !important;
        min-width: 60px !important; width: 60px !important; height: 75px !important;
        border-radius: 8px !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        margin: 0 !important; padding: 5px !important;
        display: flex !important; flex-direction: column !important; 
        justify-content: center !important; align-items: center !important;
    }}
    /* 隱藏圓點 (關鍵) */
    div[role="radiogroup"] label > div:first-child {{ display: none !important; }}
    
    /* 文字樣式 */
    div[role="radiogroup"] label p {{
        font-family: 'Times New Roman' !important; font-size: 1.6rem !important; 
        color: {current_theme['sub']} !important; margin: 0 !important; line-height: 1.1 !important;
        text-align: center !important;
    }}
    
    /* 選中狀態 */
    div[role="radiogroup"] label[data-checked="true"] {{
        background: {current_theme['primary']} !important; border-color: {current_theme['primary']} !important;
        transform: translateY(-2px);
    }}
    div[role="radiogroup"] label[data-checked="true"] p {{ color: #FFFFFF !important; }}

    /* 卡片樣式 */
    .itinerary-card, .info-card {{
        background: {current_theme['card']}; border: 1px solid #EEE; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }}
    .card-title {{ font-size: 1.2rem; font-weight: 900; color: {current_theme['text']}; }}
    .card-sub {{ color: {current_theme['sub']}; font-size: 0.9rem; }}
    .card-tag {{ background: {current_theme['primary']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: auto; }}
    
    /* 時間軸 (增加左邊距避免切到字) */
    .timeline-wrapper {{ position: relative; padding-left: 75px; }}
    .time-dot {{
        position: absolute; left: -26px; top: 20px; width: 12px; height: 12px;
        background: {current_theme['text']}; border-radius: 50%; border: 2px solid {current_theme['bg']}; z-index: 2;
    }}
    .time-label {{ position: absolute; left: -80px; top: 15px; width: 60px; text-align: right; font-weight: 900; color: {current_theme['sub']}; }}
    .connector-line {{ border-left: 2px dashed {current_theme['secondary']}; margin-left: -21px; padding-left: 21px; min-height: 40px; }}
    
    /* 按鈕與輸入框 */
    .stButton button {{ border-radius: 20px; }}
    .map-btn {{
        text-decoration: none; color: {current_theme['sub']}; border: 1px solid #EEE; 
        padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; 
        margin-left: 8px; background: {current_theme['bg']}; display: inline-flex; align-items: center;
    }}
    .expense-box {{ background-color: {current_theme['bg']}; border-top: 1px solid #EEE; margin-top: 10px; padding-top: 10px; }}
    .expense-item {{ display: flex; justify-content: space-between; font-size: 0.85rem; color: {current_theme['text']}; margin-bottom: 4px; }}
    .expense-note {{ font-size: 0.85rem; color: {current_theme['sub']}; background: {current_theme['bg']}; padding: 5px 8px; border-radius: 4px; margin-bottom: 8px; }}
    
    /* 進度條顏色 */
    div[data-testid="stProgress"] > div > div {{ background-color: {current_theme['primary']} !important; }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 6. 主畫面 Layout
# -------------------------------------

# 封面圖處理
if st.session_state.custom_cover_img:
    st.image(st.session_state.custom_cover_img, use_container_width=True)
else:
    st.image(current_theme["cover"], use_container_width=True)

# 標題區塊
c_h1, c_h2 = st.columns([5, 1])
with c_h1:
    st.markdown(f'<div style="font-size:2.2rem; font-weight:900; color:{current_theme["text"]};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
    st.caption("1/17 - 1/22")
with c_h2:
    if st.button("🎨", help="風格設定"):
        st.session_state.show_theme_modal = not st.session_state.show_theme_modal

# --- 風格設定面板 ---
if st.session_state.show_theme_modal:
    with st.container(border=True):
        c_m1, c_m2 = st.columns([5, 1])
        c_m1.markdown("### 🎨 風格設定")
        if c_m2.button("✖️"):
            st.session_state.show_theme_modal = False
            st.rerun()
        
        st.divider()
        st.markdown("##### 主題色系")
        cols = st.columns(6)
        for i, (name, style) in enumerate(THEMES.items()):
            with cols[i % 6]:
                is_active = "border: 2px solid #333;" if name == st.session_state.selected_theme_name else "border: 1px solid #ddd;"
                st.markdown(f"""<div style="background-color:{style['primary']}; width:40px; height:40px; border-radius:8px; {is_active} margin:0 auto;"></div><div style="text-align:center; font-size:0.7rem; margin-top:4px; color:#666;">{name[:2]}</div>""", unsafe_allow_html=True)
                if st.button(f"{i}", key=f"theme_btn_{name}", label_visibility="collapsed"):
                    st.session_state.selected_theme_name = name
                    st.rerun()
        
        st.divider()
        st.markdown("##### 封面照片")
        cover_src = st.radio("來源", ["系統預設", "上傳 (含裁剪)"], horizontal=True)
        if cover_src == "系統預設":
            if st.button("恢復預設"):
                st.session_state.custom_cover_img = None
                st.rerun()
        else:
            up_file = st.file_uploader("上傳", type=['jpg','png','jpeg'])
            if up_file and HAS_CROPPER:
                img = Image.open(up_file)
                cropped_img = st_cropper(img, aspectRatio=16/9, box_color=current_theme['primary'])
                if st.button("確認套用", type="primary"):
                    img_byte_arr = io.BytesIO()
                    cropped_img.save(img_byte_arr, format='PNG')
                    st.session_state.custom_cover_img = img_byte_arr.getvalue()
                    st.rerun()

# --- 設定與匯入區 ---
with st.expander("⚙️ 旅程參數與匯入"):
    st.session_state.trip_title = st.text_input("旅程標題", st.session_state.trip_title)
    c_s1, c_s2 = st.columns(2)
    with c_s1: st.session_state.exchange_rate = st.number_input("匯率", value=st.session_state.exchange_rate, step=0.001, format="%.3f")
    with c_s2: st.session_state.trip_days_count = st.number_input("天數", 1, 30, st.session_state.trip_days_count)
    uploaded_file = st.file_uploader("匯入 Excel", type=["xlsx"])
    if uploaded_file and st.button("確認匯入"): process_excel_upload(uploaded_file)

# --- 分頁 ---
tab1, tab2, tab3, tab4 = st.tabs(["📅 行程", "🗺️ 地圖", "🎒 清單", "ℹ️ 資訊"])

# ==========================================
# Tab 1: 行程規劃 (包含 5 天行程邏輯)
# ==========================================
with tab1:
    selected_day_num = st.radio("DaySelect", list(range(1, st.session_state.trip_days_count + 1)), horizontal=True, label_visibility="collapsed", format_func=lambda x: f"Day\n{x}")
    current_items = st.session_state.trip_data[selected_day_num]
    current_items.sort(key=lambda x: x['time']) # 確保排序

    st.markdown(f"<div style='font-size:2rem; font-weight:900; font-family:Times New Roman; color:{current_theme['text']};'>Day {selected_day_num}</div>", unsafe_allow_html=True)
    
    is_edit_mode = st.toggle("✏️ 編輯模式")
    if is_edit_mode and st.button("➕ 新增行程", use_container_width=True):
        st.session_state.trip_data[selected_day_num].append({"id": int(time.time()), "time":"09:00", "title":"新行程", "loc":"", "cost":0, "cat":"spot", "note":"", "expenses":[]})
        st.rerun()

    st.markdown('<div class="timeline-wrapper" style="margin-top:20px;">', unsafe_allow_html=True)
    
    if not current_items: st.info("🍵 本日尚無行程")

    for index, item in enumerate(current_items):
        # 確保資料欄位齊全
        if "expenses" not in item: item["expenses"] = []
        if "trans_min" not in item: item["trans_min"] = 30
        if "trans_mode" not in item: item["trans_mode"] = "📍 移動"

        # 計算顯示
        total_cost = sum(x['price'] for x in item['expenses'])
        disp_cost = total_cost if total_cost > 0 else item['cost']
        price_tag = f"¥{disp_cost:,}" if disp_cost > 0 else ""
        
        # HTML 組件
        icon = get_category_icon(item['cat'])
        map_btn = f'<a href="{get_single_map_link(item["loc"])}" target="_blank" class="map-btn">🗺️ 地圖</a>' if item['loc'] else ""
        note_div = f"<div class='expense-note'>📝 {item['note']}</div>" if item['note'] and not is_edit_mode else ""
        
        exp_div = ""
        if item['expenses']:
            rows = "".join([f"<div class='expense-item'><span>{e['name']}</span><span>¥{e['price']:,}</span></div>" for e in item['expenses']])
            exp_div = f"<div class='expense-box'>{rows}</div>"

        card_html = f"""
        <div style="position:relative;">
            <div class="time-label">{item['time']}</div>
            <div class="time-dot"></div>
            <div class="itinerary-card">
                <div class="card-title">{icon} {item['title']}</div>
                <div class="card-sub"><span>📍 {item['loc']}</span>{map_btn}<span class="card-tag">{price_tag}</span></div>
                {note_div}
                {exp_div}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # 編輯區塊
        if is_edit_mode:
            with st.container(border=True):
                st.caption(f"編輯：{item['title']}")
                item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                c1, c2, c3 = st.columns([3,2,1])
                c1.text_input("新增項目", key=f"new_exp_n_{item['id']}")
                c2.number_input("金額", key=f"new_exp_p_{item['id']}")
                c3.button("➕", key=f"add_{item['id']}", on_click=add_expense_callback, args=(item['id'], selected_day_num))
                
                if item['expenses']:
                    with st.expander("刪除項目"):
                        for idx, ex in enumerate(item['expenses']):
                            if st.button(f"刪除 {ex['name']}", key=f"del_ex_{item['id']}_{idx}"):
                                item['expenses'].pop(idx)
                                st.rerun()
                
                st.divider()
                c_t1, c_t2 = st.columns(2)
                item['title'] = c_t1.text_input("名稱", item['title'], key=f"tt_{item['id']}")
                item['loc'] = c_t2.text_input("地點", item['loc'], key=f"ll_{item['id']}")
                t_val = datetime.strptime(item['time'], "%H:%M").time()
                item['time'] = c_t1.time_input("時間", t_val, key=f"ti_{item['id']}").strftime("%H:%M")
                if st.button("🗑️ 刪除行程", key=f"del_it_{item['id']}"):
                    st.session_state.trip_data[selected_day_num].pop(index)
                    st.rerun()

        # 交通連接線
        if index < len(current_items) - 1:
            if is_edit_mode:
                st.markdown('<div class="connector-line">', unsafe_allow_html=True)
                cc1, cc2 = st.columns([2,1])
                item['trans_mode'] = cc1.selectbox("交通", TRANSPORT_OPTIONS, index=0, key=f"tm_{item['id']}", label_visibility="collapsed")
                item['trans_min'] = cc2.number_input("分", value=item['trans_min'], step=5, key=f"tmin_{item['id']}", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="connector-line"><span class="travel-badge">{item["trans_mode"]} 約 {item["trans_min"]} 分</span></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    if current_items:
        g_url = generate_google_map_route(current_items)
        st.markdown(f"<div style='text-align:center; margin-top:20px;'><a href='{g_url}' target='_blank' style='background:{current_theme['primary']}; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 開啟本日導航</a></div>", unsafe_allow_html=True)

# ==========================================
# Tab 2: 路線全覽
# ==========================================
with tab2:
    st.markdown(f'<div class="retro-subtitle" style="font-weight:900; color:{current_theme["sub"]}; text-align:center;">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
    map_d = st.selectbox("選擇天數", list(range(1, st.session_state.trip_days_count + 1)), format_func=lambda x: f"Day {x}", key="map_day")
    m_items = sorted(st.session_state.trip_data[map_d], key=lambda x: x['time'])
    
    if m_items:
        html = ['<div class="map-tl-container">']
        for i, it in enumerate(m_items):
            ic = get_category_icon(it['cat'])
            html.append(f"""
            <div class='map-tl-item' style='animation-delay:{i*0.1}s'>
                <div class='map-tl-icon'>{ic}</div>
                <div class='map-tl-content'>
                    <div style='color:{current_theme['primary']}; font-weight:bold;'>{it['time']}</div>
                    <div style='font-weight:900; font-size:1.1rem; color:{current_theme['text']};'>{it['title']}</div>
                    <div style='font-size:0.85rem; color:{current_theme['sub']};'>{it['loc']}</div>
                </div>
            </div>""")
        html.append('</div>')
        st.markdown("".join(html), unsafe_allow_html=True)
    else:
        st.info("🌸 本日尚無行程")

# ==========================================
# Tab 3: 準備清單
# ==========================================
with tab3:
    c_l1, c_l2 = st.columns([3,1])
    c_l1.markdown("### 🎒 行李清單")
    edit_l = c_l2.toggle("編輯")
    
    for cat, items in st.session_state.checklist.items():
        st.markdown(f"**{cat}**")
        cols = st.columns(2)
        to_del = []
        for i, (k, v) in enumerate(items.items()):
            if edit_l:
                c_e1, c_e2 = cols[i%2].columns([4,1])
                c_e1.text(k)
                if c_e2.button("x", key=f"d_{cat}_{k}"): to_del.append(k)
            else:
                st.session_state.checklist[cat][k] = cols[i%2].checkbox(k, v, key=f"c_{cat}_{k}")
        
        if to_del:
            for k in to_del: del st.session_state.checklist[cat][k]
            st.rerun()
            
        if edit_l:
            new = st.text_input(f"新增至 {cat}", key=f"n_{cat}")
            if new and st.button("加入", key=f"b_{cat}"):
                st.session_state.checklist[cat][new] = False
                st.rerun()

# ==========================================
# Tab 4: 重要資訊
# ==========================================
with tab4:
    c_i1, c_i2 = st.columns([3,1])
    c_i1.markdown("### ✈️ 航班")
    edit_i = c_i2.toggle("編輯", key="edit_info")
    
    f = st.session_state.flight_info
    # (簡化顯示，邏輯同前)
    st.markdown(f"""<div class="info-card"><div class="info-header"><span>{f['outbound']['date']}</span><span>{f['outbound']['code']}</span></div><div class="info-time">{f['outbound']['dep']} ➝ {f['outbound']['arr']}</div></div>""", unsafe_allow_html=True)
    
    st.markdown("### 🏨 住宿")
    if edit_i and st.button("➕ 住宿"):
        st.session_state.hotel_info.append({"id": int(time.time()), "name":"新住宿", "range":"", "date":"", "addr":"", "link":""})
        st.rerun()
        
    for i, h in enumerate(st.session_state.hotel_info):
        if edit_i:
            with st.expander(f"編輯 {h['name']}", expanded=True):
                h['name'] = st.text_input("飯店", h['name'], key=f"hn_{h['id']}")
                h['addr'] = st.text_input("地址", h['addr'], key=f"ha_{h['id']}")
                if st.button("刪除", key=f"hd_{h['id']}"):
                    st.session_state.hotel_info.pop(i)
                    st.rerun()
        
        st.markdown(f"""<div class="info-card" style="border-left: 5px solid {current_theme['primary']};"><div class="info-header"><span>{h['range']}</span></div><div style="font-size:1.2rem; font-weight:bold; color:{current_theme['text']};">{h['name']}</div><div class="info-loc">📍 {h['addr']}</div></div>""", unsafe_allow_html=True)