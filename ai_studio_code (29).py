import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
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

THEMES = {
    "京都緋紅": {"bg": "#FDFCF5", "card": "#FFFFFF", "text": "#2B2B2B", "primary": "#8E2F2F", "secondary": "#D6A6A6", "sub": "#666666", "cover": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e"},
    "宇治抹茶": {"bg": "#F7FAF5", "card": "#FFFFFF", "text": "#1C3318", "primary": "#557C55", "secondary": "#C6EBC5", "sub": "#405D40", "cover": "https://images.unsplash.com/photo-1624253321171-1be53e12f5f4"},
    "莫蘭迪藍": {"bg": "#F0F4F8", "card": "#FFFFFF", "text": "#243B53", "primary": "#486581", "secondary": "#BCCCDC", "sub": "#627D98", "cover": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e"},
    "焦糖奶茶": {"bg": "#FAF6F1", "card": "#FFFFFF", "text": "#4A3B32", "primary": "#9C7C64", "secondary": "#E0D0C5", "sub": "#7D6556", "cover": "https://images.unsplash.com/photo-1469334031218-e382a71b716b"},
    "江戶紫鳶": {"bg": "#F8F5FA", "card": "#FFFFFF", "text": "#2D2436", "primary": "#6B4C75", "secondary": "#D6BCFA", "sub": "#553C9A", "cover": "https://images.unsplash.com/photo-1492571350019-22de08371fd3"},
    "現代極簡": {"bg": "#F5F5F5", "card": "#FFFFFF", "text": "#1A1A1A", "primary": "#4A4A4A", "secondary": "#CCCCCC", "sub": "#666666", "cover": "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b"}
}

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船", "✈️ 飛機"]

# -------------------------------------
# 3. 核心功能函數
# -------------------------------------

def add_expense_callback(item_id, day_num):
    name_key = f"new_exp_n_{item_id}"
    price_key = f"new_exp_p_{item_id}"
    name = st.session_state.get(name_key, "")
    price = st.session_state.get(price_key, 0)
    if name and price > 0:
        target_item = next((x for x in st.session_state.trip_data[day_num] if x['id'] == item_id), None)
        if target_item:
            target_item.setdefault("expenses", []).append({"name": name, "price": price})
            target_item['cost'] = sum(x['price'] for x in target_item['expenses'])
            st.session_state[name_key] = ""
            st.session_state[price_key] = 0

def get_single_map_link(location):
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(location)}" if location else "#"

def generate_google_map_route(items):
    valid_locs = [item['loc'] for item in items if item.get('loc') and item['loc'].strip()]
    if not valid_locs: return "#"
    return "https://www.google.com/maps/dir/" + "/".join([urllib.parse.quote(loc) for loc in valid_locs])

def get_category_icon(cat):
    return {"trans": "🚃", "food": "🍱", "stay": "🏨", "spot": "⛩️", "shop": "🛍️"}.get(cat, "📍")

def process_excel_upload(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        required = ['Day', 'Time', 'Title']
        if not all(c in df.columns for c in required):
            st.error("Excel 缺少必要欄位")
            return
        new_data = {}
        for _, row in df.iterrows():
            d = int(row['Day'])
            if d not in new_data: new_data[d] = []
            t_str = row['Time'].strftime("%H:%M") if isinstance(row['Time'], (datetime, pd.Timestamp)) else str(row['Time'])
            new_data[d].append({
                "id": int(time.time()*1000)+_, "time": t_str, "title": str(row['Title']),
                "loc": str(row.get('Location','')), "cost": int(row.get('Cost',0)),
                "cat": "other", "note": str(row.get('Note','')), "expenses": [],
                "trans_mode": "📍 移動", "trans_min": 30
            })
        st.session_state.trip_data = new_data
        st.session_state.trip_days_count = max(new_data.keys())
        st.rerun()
    except Exception as e:
        st.error(f"匯入失敗: {e}")

# -------------------------------------
# 4. 初始化
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "京都緋紅"
if "custom_cover_img" not in st.session_state: st.session_state.custom_cover_img = None
if "show_theme_modal" not in st.session_state: st.session_state.show_theme_modal = False

current_theme = THEMES[st.session_state.selected_theme_name]

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id": 101, "time": "10:00", "title": "抵達關西機場", "loc": "關西機場", "cost": 0, "cat": "trans", "note": "領取周遊券", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 75},
            {"id": 102, "time": "13:00", "title": "Check-in", "loc": "KOKO HOTEL 京都", "cost": 0, "cat": "stay", "note": "", "expenses": [], "trans_mode": "🚌 巴士", "trans_min": 20},
            {"id": 103, "time": "15:00", "title": "錦市場", "loc": "錦市場", "cost": 2000, "cat": "food", "note": "吃午餐", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 104, "time": "18:00", "title": "鴨川散步", "loc": "鴨川", "cost": 0, "cat": "spot", "note": "夜景", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}],
        2: [{"id": 201, "time": "09:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "cat": "spot", "note": "", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 20},
            {"id": 202, "time": "11:00", "title": "二三年坂", "loc": "三年坂", "cost": 1000, "cat": "spot", "note": "", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15},
            {"id": 203, "time": "13:00", "title": "八坂神社", "loc": "八坂神社", "cost": 0, "cat": "spot", "note": "", "expenses": [], "trans_mode": "🚌 巴士", "trans_min": 30},
            {"id": 204, "time": "16:00", "title": "金閣寺", "loc": "金閣寺", "cost": 400, "cat": "spot", "note": "", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}],
        3: [{"id": 301, "time": "09:00", "title": "伏見稻荷大社", "loc": "伏見稻荷大社", "cost": 0, "cat": "spot", "note": "", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 45},
            {"id": 302, "time": "13:00", "title": "奈良公園", "loc": "奈良公園", "cost": 200, "cat": "spot", "note": "", "expenses": [], "trans_mode": "🚶 步行", "trans_min": 15}],
        4: [{"id": 401, "time": "09:30", "title": "環球影城 (USJ)", "loc": "環球影城", "cost": 9000, "cat": "spot", "note": "", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 40},
            {"id": 402, "time": "19:00", "title": "道頓堀", "loc": "道頓堀", "cost": 3000, "cat": "food", "note": "", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}],
        5: [{"id": 501, "time": "10:00", "title": "黑門市場", "loc": "黑門市場", "cost": 2000, "cat": "food", "note": "", "expenses": [], "trans_mode": "🚆 電車", "trans_min": 50},
            {"id": 503, "time": "16:00", "title": "前往機場", "loc": "關西機場", "cost": 0, "cat": "trans", "note": "", "expenses": [], "trans_mode": "✈️ 飛機", "trans_min": 0}]
    }

for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {"outbound": {"date": "1/17", "code": "JX821", "dep": "10:00", "arr": "13:30", "dep_loc": "T1", "arr_loc": "KIX"}, "inbound": {"date": "1/22", "code": "JX822", "dep": "15:00", "arr": "17:10", "dep_loc": "KIX", "arr_loc": "T1"}}

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [{"id": 1, "name": "KOKO HOTEL 京都", "range": "D1-D3", "date": "1/17-1/19", "addr": "京都...", "link": "#"}]

if "checklist" not in st.session_state:
    st.session_state.checklist = {"必要證件": {"護照": False, "日幣": False}, "電子產品": {"手機": False, "充電器": False}, "衣物": {"換洗衣物": False, "外套": False}}

# -------------------------------------
# 5. CSS 樣式 (修復版型)
# -------------------------------------
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp {{ background-color: {current_theme['bg']} !important; color: {current_theme['text']} !important; font-family: 'Noto Serif JP', serif !important; }}
    
    [data-testid="stSidebarCollapsedControl"], footer, header {{ display: none !important; }}
    
    /* Day 按鈕 (強制修復) */
    div[role="radiogroup"] {{
        display: flex !important; flex-direction: row !important; overflow-x: auto !important;
        gap: 8px !important; padding: 5px 2px !important; width: 100% !important;
        flex-wrap: nowrap !important;
    }}
    div[role="radiogroup"] label {{
        background: {current_theme['card']} !important; border: 1px solid #DDD !important;
        min-width: 65px !important; width: 65px !important; height: 70px !important;
        border-radius: 8px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        margin: 0 !important; padding: 0 !important;
        display: flex !important; flex-direction: column !important; 
        justify-content: center !important; align-items: center !important;
        flex-shrink: 0 !important;
    }}
    div[role="radiogroup"] label p {{
        font-family: 'Times New Roman' !important; font-size: 1.4rem !important; 
        color: {current_theme['sub']} !important; margin: 0 !important; line-height: 1.2 !important;
    }}
    div[role="radiogroup"] label p::first-line {{ font-size: 0.8rem !important; color: #AAA !important; }}
    div[role="radiogroup"] label[data-checked="true"] {{
        background: {current_theme['primary']} !important; border-color: {current_theme['primary']} !important;
    }}
    div[role="radiogroup"] label[data-checked="true"] p {{ color: #FFFFFF !important; }}
    div[role="radiogroup"] label > div:first-child {{ display: none !important; }}

    /* 卡片樣式 */
    .itinerary-card, .info-card {{
        background: {current_theme['card']}; border: 1px solid #EEE; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        position: relative; z-index: 2;
    }}
    .card-title {{ font-size: 1.2rem; font-weight: 900; color: {current_theme['text']}; margin-bottom: 4px; }}
    .card-sub {{ color: {current_theme['sub']}; font-size: 0.9rem; display: flex; align-items: center; gap: 5px; }}
    .card-tag {{ background: {current_theme['primary']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: auto; float: right; }}
    
    /* 時間軸 */
    .timeline-wrapper {{ position: relative; padding-left: 75px; }}
    .time-dot {{
        position: absolute; left: -26px; top: 20px; width: 12px; height: 12px;
        background: {current_theme['text']}; border-radius: 50%; border: 2px solid {current_theme['bg']}; z-index: 2;
    }}
    .time-label {{ position: absolute; left: -80px; top: 15px; width: 60px; text-align: right; font-weight: 900; color: {current_theme['sub']}; }}
    .connector-line {{ border-left: 2px dashed {current_theme['secondary']}; margin-left: -21px; padding-left: 21px; min-height: 40px; display: flex; align-items: center; position: relative; z-index: 1; }}
    .travel-badge {{
        background-color: {current_theme['card']}; border: 1px solid #DDD; border-radius: 6px;
        padding: 4px 8px; font-size: 0.75rem; color: {current_theme['sub']};
    }}

    /* 其他 */
    .stButton button {{ border-radius: 20px; }}
    .map-btn {{
        text-decoration: none; color: {current_theme['sub']}; border: 1px solid #EEE; 
        padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; margin-left: 8px; background: {current_theme['bg']};
    }}
    .expense-box {{ background-color: {current_theme['bg']}; border-top: 1px solid #EEE; margin-top: 8px; padding-top: 8px; font-size: 0.8rem; }}
    .expense-item {{ display: flex; justify-content: space-between; margin-bottom: 3px; color: {current_theme['text']}; }}
    .expense-note {{ font-size: 0.85rem; color: {current_theme['sub']}; background: {current_theme['bg']}; padding: 5px 8px; border-radius: 4px; margin-bottom: 8px; }}
    
    /* 修正分頁按鈕 */
    button[data-baseweb="tab"] {{ padding: 10px 15px !important; min-width: 60px; }}
    
    /* 動態時間軸樣式 (Tab 2) */
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
    
    /* Info Card */
    .info-header {{ display: flex; justify-content: space-between; margin-bottom: 5px; color: {current_theme['sub']}; font-size: 0.85rem; }}
    .info-time {{ font-size: 1.5rem; font-weight: bold; color: {current_theme['text']}; margin-bottom: 5px; font-family: 'Times New Roman'; }}
    .info-loc {{ font-size: 0.9rem; color: {current_theme['sub']}; }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 6. 主畫面 Layout
# -------------------------------------

# 封面圖
if st.session_state.custom_cover_img:
    st.image(st.session_state.custom_cover_img, use_container_width=True)
else:
    st.image(current_theme["cover"], use_container_width=True)

# 標題
c_h1, c_h2 = st.columns([5, 1])
with c_h1:
    st.markdown(f'<div style="font-size:2rem; font-weight:900; color:{current_theme["text"]};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
    st.caption("1/17 - 1/22")
with c_h2:
    if st.button("🎨"):
        st.session_state.show_theme_modal = not st.session_state.show_theme_modal

# --- 風格設定 ---
if st.session_state.show_theme_modal:
    with st.container(border=True):
        c_m1, c_m2 = st.columns([5, 1])
        c_m1.markdown("### 風格設定")
        if c_m2.button("✖️"):
            st.session_state.show_theme_modal = False
            st.rerun()
        
        st.markdown("##### 選擇主題")
        cols = st.columns(4)
        for i, t_name in enumerate(THEMES.keys()):
            with cols[i % 4]:
                if st.button(t_name[:2], key=f"btn_theme_{i}"):
                    st.session_state.selected_theme_name = t_name
                    st.rerun()
        
        st.divider()
        st.markdown("##### 封面")
        src = st.radio("來源", ["預設", "上傳"], horizontal=True)
        if src == "預設":
            if st.button("恢復"):
                st.session_state.custom_cover_img = None
                st.rerun()
        else:
            up = st.file_uploader("圖片", type=['jpg','png'])
            if up and HAS_CROPPER:
                img = Image.open(up)
                cropped = st_cropper(img, aspectRatio=16/9, box_color=current_theme['primary'])
                if st.button("套用"):
                    b = io.BytesIO()
                    cropped.save(b, format='PNG')
                    st.session_state.custom_cover_img = b.getvalue()
                    st.rerun()

with st.expander("⚙️ 設定與匯入"):
    st.session_state.trip_title = st.text_input("標題", st.session_state.trip_title)
    c_s1, c_s2 = st.columns(2)
    with c_s1: st.session_state.exchange_rate = st.number_input("匯率", 0.215)
    with c_s2: st.session_state.trip_days_count = st.number_input("天數", 1, 30, 5)
    
    st.session_state.target_country = st.selectbox("旅遊資訊地區", ["日本", "韓國", "泰國", "台灣"])
    
    up_xls = st.file_uploader("匯入 Excel", type=["xlsx"])
    if up_xls and st.button("確認"): process_excel_upload(up_xls)

tab1, tab2, tab3, tab4 = st.tabs(["📅 行程", "🗺️ 地圖", "🎒 清單", "ℹ️ 資訊"])

# ==========================================
# Tab 1: 行程 (HTML 修復)
# ==========================================
with tab1:
    sel_day = st.radio("Day", list(range(1, st.session_state.trip_days_count + 1)), horizontal=True, label_visibility="collapsed", format_func=lambda x: f"Day\n{x}")
    day_items = st.session_state.trip_data[sel_day]
    day_items.sort(key=lambda x: x['time'])

    st.markdown(f"<div style='font-size:1.8rem; font-weight:bold; color:{current_theme['text']}; margin-top:10px;'>Day {sel_day}</div>", unsafe_allow_html=True)
    
    is_edit = st.toggle("編輯模式")
    if is_edit and st.button("➕ 新增"):
        st.session_state.trip_data[sel_day].append({"id": int(time.time()), "time":"09:00", "title":"新行程", "loc":"", "cost":0, "cat":"spot", "note":"", "expenses":[]})
        st.rerun()

    st.markdown('<div class="timeline-wrapper" style="margin-top:20px;">', unsafe_allow_html=True)
    
    if not day_items: st.info("無行程")

    for idx, item in enumerate(day_items):
        # 資料補齊
        item.setdefault("expenses", [])
        item.setdefault("trans_mode", "📍")
        item.setdefault("trans_min", 30)

        # 計算
        cost = sum(x['price'] for x in item['expenses'])
        disp_cost = cost if cost > 0 else item['cost']
        twd = int(disp_cost * st.session_state.exchange_rate)
        price_txt = f"¥{disp_cost:,} (NT${twd:,})" if disp_cost > 0 else ""
        
        # HTML 組合 (關鍵：不縮排)
        icon = get_category_icon(item['cat'])
        map_url = get_single_map_link(item['loc'])
        map_link = f'<a href="{map_url}" target="_blank" class="map-btn">地圖</a>' if item['loc'] else ""
        note_html = f"<div class='expense-note'>📝 {item['note']}</div>" if item['note'] and not is_edit else ""
        
        exp_html = ""
        if item['expenses']:
            rows = "".join([f"<div class='expense-item'><span>{e['name']}</span><span>¥{e['price']:,}</span></div>" for e in item['expenses']])
            exp_html = f"<div class='expense-box'>{rows}</div>"

        # 卡片本體 HTML
        card_html = f"""
<div style="position:relative;">
    <div class="time-label">{item['time']}</div>
    <div class="time-dot"></div>
    <div class="itinerary-card">
        <div class="card-title">{icon} {item['title']}</div>
        <div class="card-sub"><span>📍 {item['loc']}</span>{map_link}<span class="card-tag">{price_txt}</span></div>
        {note_html}
        {exp_html}
    </div>
</div>
"""
        # 移除換行符號，避免 Streamlit 解析錯誤
        st.markdown(card_html.replace("\n", ""), unsafe_allow_html=True)

        # 編輯區
        if is_edit:
            with st.container(border=True):
                item['title'] = st.text_input("名稱", item['title'], key=f"t_{item['id']}")
                item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                
                c1, c2, c3 = st.columns([3,2,1])
                c1.text_input("細項", key=f"new_exp_n_{item['id']}")
                c2.number_input("¥", key=f"new_exp_p_{item['id']}")
                c3.button("➕", key=f"add_{item['id']}", on_click=add_expense_callback, args=(item['id'], sel_day))
                
                if item['expenses']:
                    if st.button("清空細項", key=f"clr_{item['id']}"):
                        item['expenses'] = []
                        st.rerun()
                
                if st.button("🗑️ 刪除", key=f"del_{item['id']}"):
                    st.session_state.trip_data[sel_day].pop(idx)
                    st.rerun()

        # 交通
        if idx < len(day_items) - 1:
            if is_edit:
                st.markdown('<div class="connector-line">', unsafe_allow_html=True)
                c_t1, c_t2 = st.columns([2,1])
                item['trans_mode'] = c_t1.selectbox("交通", TRANSPORT_OPTIONS, key=f"tm_{item['id']}", label_visibility="collapsed")
                item['trans_min'] = c_t2.number_input("分", value=item['trans_min'], step=5, key=f"tmin_{item['id']}", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="connector-line"><span class="travel-badge">{item["trans_mode"]} {item["trans_min"]}分</span></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    if day_items:
        g_url = generate_google_map_route(day_items)
        st.markdown(f"<div style='text-align:center; margin-top:20px;'><a href='{g_url}' target='_blank' style='background:{current_theme['primary']}; color:white; padding:8px 20px; border-radius:30px; text-decoration:none; font-size:0.9rem;'>🚗 Google Maps 導航</a></div>", unsafe_allow_html=True)

# ==========================================
# Tab 2: 路線全覽
# ==========================================
with tab2:
    st.markdown(f'<div class="retro-subtitle" style="font-weight:900; color:{current_theme["sub"]}; text-align:center;">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
    map_d = st.selectbox("選擇天數", list(range(1, st.session_state.trip_days_count + 1)), format_func=lambda x: f"Day {x}", key="map_day")
    m_items = sorted(st.session_state.trip_data[map_d], key=lambda x: x['time'])
    
    if m_items:
        html_items = "".join([
            f"<div class='map-tl-item' style='animation-delay:{i*0.1}s'><div class='map-tl-icon'>{get_category_icon(it['cat'])}</div><div class='map-tl-content'><div style='color:{current_theme['primary']}; font-weight:bold;'>{it['time']}</div><div style='font-weight:900; font-size:1.1rem; color:{current_theme['text']};'>{it['title']}</div><div style='font-size:0.85rem; color:{current_theme['sub']};'>{it['loc']}</div></div></div>"
            for i, it in enumerate(m_items)
        ])
        st.markdown(f"<div class='map-tl-container'>{html_items}</div>", unsafe_allow_html=True)
    else:
        st.info("🌸 本日尚無行程")

# ==========================================
# Tab 3: 清單 (含旅遊資訊)
# ==========================================
with tab3:
    c1, c2 = st.columns([3,1])
    c1.markdown("### 🎒 清單")
    ed = c2.toggle("編輯", key="ed_list")
    for k, v in st.session_state.checklist.items():
        st.markdown(f"**{k}**")
        cols = st.columns(2)
        for i, (sub, checked) in enumerate(v.items()):
            if ed:
                if cols[i%2].button(f"刪 {sub}", key=f"del_{k}_{sub}"):
                    del st.session_state.checklist[k][sub]
                    st.rerun()
            else:
                st.session_state.checklist[k][sub] = cols[i%2].checkbox(sub, checked, key=f"chk_{k}_{sub}")
    if ed:
        new = st.text_input("新增項目", key="new_item")
        cat = st.selectbox("分類", list(st.session_state.checklist.keys()), key="new_cat")
        if new and st.button("加入清單"):
            st.session_state.checklist[cat][new] = False
            st.rerun()

    st.divider()
    country = st.session_state.get("target_country", "日本")
    st.markdown(f"### 🌍 當地旅遊資訊 ({country})")
    
    now = datetime.now()
    month = now.month
    season_info = ""
    weather_icon = "🌤️"
    
    if 3 <= month <= 5:
        season_info = "春季：氣候宜人但早晚偏涼，適合洋蔥式穿搭，建議帶一件薄外套。"
        weather_icon = "🌸"
    elif 6 <= month <= 8:
        season_info = "夏季：炎熱潮濕，注意防曬與補充水分，室內冷氣較強，可帶薄衫。"
        weather_icon = "☀️"
    elif 9 <= month <= 11:
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

    i1, i2 = st.columns(2)
    i1.info(f"**{weather_icon} 氣候建議**\n\n{season_info}")
    i2.success(f"**🔌 電壓**\n\n{voltage_info}")
    i1.warning(f"**🚑 緊急電話**\n\n{sos_info}")
    i2.error(f"**💴 小費與消費**\n\n{tip_info}")

# ==========================================
# Tab 4: 重要資訊 (完全恢復)
# ==========================================
with tab4:
    c1, c2 = st.columns([3,1])
    c1.markdown("### ✈️ 航班")
    edit_i = c2.toggle("編輯", key="edit_info")
    
    f = st.session_state.flight_info
    
    if edit_i:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            f['outbound']['date'] = c1.text_input("去程日期", f['outbound']['date'])
            f['outbound']['code'] = c2.text_input("航班", f['outbound']['code'])
            f['outbound']['dep'] = c1.text_input("起飛", f['outbound']['dep'])
            f['outbound']['arr'] = c2.text_input("抵達", f['outbound']['arr'])
    
    st.markdown(f"""<div class="info-card"><div class="info-header"><span>去程 {f['outbound']['date']}</span><span>{f['outbound']['code']}</span></div><div class="info-time">{f['outbound']['dep']} ➝ {f['outbound']['arr']}</div><div class="info-loc"><span>{f['outbound']['dep_loc']}</span> ➝ <span>{f['outbound']['arr_loc']}</span></div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div class="info-card"><div class="info-header"><span>回程 {f['inbound']['date']}</span><span>{f['inbound']['code']}</span></div><div class="info-time">{f['inbound']['dep']} ➝ {f['inbound']['arr']}</div><div class="info-loc"><span>{f['inbound']['dep_loc']}</span> ➝ <span>{f['inbound']['arr_loc']}</span></div></div>""", unsafe_allow_html=True)
    
    st.markdown("### 🏨 住宿")
    if edit_i and st.button("➕ 住宿"):
        st.session_state.hotel_info.append({"id": int(time.time()), "name":"新住宿", "range":"", "date":"", "addr":"", "link":""})
        st.rerun()
        
    for i, h in enumerate(st.session_state.hotel_info):
        if edit_i:
            with st.expander(f"編輯 {h['name']}", expanded=True):
                h['name'] = st.text_input("飯店", h['name'], key=f"hn_{h['id']}")
                h['addr'] = st.text_input("地址", h['addr'], key=f"ha_{h['id']}")
                h['range'] = st.text_input("天數", h['range'], key=f"hr_{h['id']}")
                if st.button("刪除", key=f"hd_{h['id']}"):
                    st.session_state.hotel_info.pop(i)
                    st.rerun()
        
        st.markdown(f"""<div class="info-card" style="border-left: 5px solid {current_theme['primary']};"><div class="info-header"><span>{h['range']}</span></div><div style="font-size:1.2rem; font-weight:bold; color:{current_theme['text']};">{h['name']}</div><div class="info-loc">📍 {h['addr']}</div></div>""", unsafe_allow_html=True)