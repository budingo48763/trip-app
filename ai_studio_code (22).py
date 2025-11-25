import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd
from PIL import Image
import io

# 嘗試匯入圖片裁剪工具，若無則提示
try:
    from streamlit_cropper import st_cropper
    HAS_CROPPER = True
except ImportError:
    HAS_CROPPER = False

# -------------------------------------
# 1. 系統設定 & 主題資料庫
# -------------------------------------
st.set_page_config(page_title="2026 旅程規劃", page_icon="✈️", layout="centered", initial_sidebar_state="collapsed")

# 🎨 主題配色與預設封面庫
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

# -------------------------------------
# 2. 核心功能函數
# -------------------------------------

# 初始化 Session State
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "京都緋紅"
if "custom_cover_img" not in st.session_state: st.session_state.custom_cover_img = None
if "show_theme_modal" not in st.session_state: st.session_state.show_theme_modal = False

current_theme = THEMES[st.session_state.selected_theme_name]

# 圖片處理函數
def render_cover_image():
    # 優先顯示使用者上傳並裁剪後的圖片，否則顯示主題預設圖
    if st.session_state.custom_cover_img:
        st.image(st.session_state.custom_cover_img, use_container_width=True)
    else:
        st.image(current_theme["cover"], use_container_width=True)

def theme_selector_ui():
    st.markdown("##### 🎨 主題色系")
    
    # 使用 Columns 模擬色票按鈕
    cols = st.columns(6)
    for i, (name, style) in enumerate(THEMES.items()):
        with cols[i % 6]:
            # 這裡用一點 HTML hack 來顯示色票，因為 st.button 不能改背景色
            # 實際上點擊是透過下方的 invisible button 或 callback (Streamlit 限制較多，這裡用 radio 模擬視覺)
            is_active = "border: 2px solid #333;" if name == st.session_state.selected_theme_name else "border: 1px solid #ddd;"
            st.markdown(f"""
            <div style="background-color:{style['primary']}; width:40px; height:40px; border-radius:8px; {is_active} margin:0 auto;"></div>
            <div style="text-align:center; font-size:0.7rem; margin-top:4px; color:#666;">{name[:2]}</div>
            """, unsafe_allow_html=True)
            
            if st.button(f"選{i}", key=f"theme_btn_{name}", label_visibility="collapsed"):
                st.session_state.selected_theme_name = name
                st.rerun()

def cover_upload_ui():
    st.markdown("##### 🖼️ 封面照片")
    
    # 選項：使用預設 vs 上傳
    cover_source = st.radio("來源", ["系統預設", "自行上傳 (含裁剪)"], horizontal=True, label_visibility="collapsed")
    
    if cover_source == "系統預設":
        if st.button("恢復預設封面"):
            st.session_state.custom_cover_img = None
            st.rerun()
        st.image(current_theme["cover"], caption="目前主題預設圖", width=300)
        
    else:
        uploaded_file = st.file_uploader("上傳照片 (支援 jpg, png)", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            if HAS_CROPPER:
                image = Image.open(uploaded_file)
                st.caption("👇 請拖曳方框裁剪圖片")
                # 裁剪器
                cropped_img = st_cropper(image, aspectRatio=16/9, box_color=current_theme['primary'])
                
                if st.button("✅ 確認裁剪並套用", type="primary"):
                    # 將 PIL Image 轉為 BytesIO 以便存入 Session
                    img_byte_arr = io.BytesIO()
                    cropped_img.save(img_byte_arr, format='PNG')
                    st.session_state.custom_cover_img = img_byte_arr.getvalue() # 存二進制資料
                    st.rerun()
            else:
                st.warning("⚠️ 缺少 `streamlit-cropper` 套件，無法使用裁剪功能。請在 requirements.txt 加入該套件。")

# -------------------------------------
# 3. CSS 樣式 (動態注入顏色)
# -------------------------------------
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp {{ background-color: {current_theme['bg']} !important; color: {current_theme['text']} !important; font-family: 'Noto Serif JP', serif !important; }}
    
    /* 隱藏預設 */
    [data-testid="stSidebarCollapsedControl"], footer, header {{ display: none !important; }}
    
    /* Day 按鈕 */
    div[data-testid="stRadio"] > div {{ display: flex; overflow-x: auto; gap: 10px; padding-bottom: 5px; }}
    div[data-testid="stRadio"] label {{
        background: {current_theme['card']}; border: 1px solid #E0E0E0; min-width: 60px; height: 75px;
        border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); justify-content: center;
    }}
    div[data-testid="stRadio"] label p {{ font-family: 'Times New Roman'; font-size: 1.6rem; color: {current_theme['sub']}; margin: 0; }}
    div[data-testid="stRadio"] label[data-checked="true"] {{
        background: {current_theme['primary']}; border-color: {current_theme['primary']}; color: white; transform: translateY(-2px);
    }}
    div[data-testid="stRadio"] label[data-checked="true"] p {{ color: white !important; }}
    
    /* 卡片樣式 */
    .itinerary-card, .info-card {{
        background: {current_theme['card']}; border: 1px solid #EEE; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }}
    .card-title {{ font-size: 1.2rem; font-weight: 900; color: {current_theme['text']}; }}
    .card-sub {{ color: {current_theme['sub']}; font-size: 0.9rem; }}
    .card-tag {{ background: {current_theme['primary']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: auto; }}
    
    /* 時間軸 */
    .timeline-wrapper {{ position: relative; padding-left: 75px; }}
    .time-dot {{
        position: absolute; left: -26px; top: 20px; width: 12px; height: 12px;
        background: {current_theme['text']}; border-radius: 50%; border: 2px solid {current_theme['bg']}; z-index: 2;
    }}
    .time-label {{ position: absolute; left: -80px; top: 15px; width: 60px; text-align: right; font-weight: 900; color: {current_theme['sub']}; }}
    .connector-line {{ border-left: 2px dashed {current_theme['secondary']}; margin-left: -21px; padding-left: 21px; min-height: 40px; }}
    
    /* 按鈕與輸入框 */
    .stButton button {{ border-radius: 20px; }}
    div[data-baseweb="input"] {{ border-bottom: 1px solid {current_theme['secondary']} !important; background: transparent !important; border: none; }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 4. 資料與邏輯 (保留原有功能)
# -------------------------------------
# (這裡保留原本的資料初始化、計算邏輯，為節省篇幅簡化，實際使用請保留原本的完整邏輯)
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {1: [{"id": 1, "time": "10:00", "title": "抵達關西", "loc": "KIX", "cost": 0, "cat": "trans", "note": "", "expenses": [], "trans_mode": "📍", "trans_min": 30}]}
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "checklist" not in st.session_state: st.session_state.checklist = {"證件": {"護照":False}}
if "flight_info" not in st.session_state: st.session_state.flight_info = {"outbound":{"date":"1/1","code":"JX800","dep":"10:00","arr":"14:00","dep_loc":"TPE","arr_loc":"NRT"}, "inbound":{"date":"1/5","code":"JX801","dep":"15:00","arr":"18:00","dep_loc":"NRT","arr_loc":"TPE"}}
if "hotel_info" not in st.session_state: st.session_state.hotel_info = []

# --- 主畫面 ---

# 封面圖區塊 (全寬)
render_cover_image()

# 標題與設定按鈕
c_h1, c_h2 = st.columns([5, 1])
with c_h1:
    st.markdown(f'<div style="font-size:2.2rem; font-weight:900; color:{current_theme["text"]};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
    st.caption("1/17 - 1/22")
with c_h2:
    if st.button("🎨", help="風格設定"):
        st.session_state.show_theme_modal = not st.session_state.show_theme_modal

# --- 風格設定面板 (模擬 Modal) ---
if st.session_state.show_theme_modal:
    with st.container(border=True):
        c_m1, c_m2 = st.columns([5, 1])
        c_m1.markdown("### 🎨 風格設定")
        if c_m2.button("✖️", key="close_modal"):
            st.session_state.show_theme_modal = False
            st.rerun()
        
        st.divider()
        theme_selector_ui() # 色票選擇
        st.divider()
        cover_upload_ui()   # 封面圖上傳與裁切
        st.divider()
        
        if st.button("完成設定", use_container_width=True, type="primary"):
            st.session_state.show_theme_modal = False
            st.rerun()

# --- 一般設定 (隱藏在 Expander) ---
with st.expander("⚙️ 旅程參數與匯入"):
    st.session_state.trip_title = st.text_input("旅程標題", st.session_state.trip_title)
    st.session_state.trip_days_count = st.number_input("天數", 1, 30, st.session_state.trip_days_count)
    # (這裡可以放原本的 Excel 匯入功能)

# --- 分頁內容 ---
tab1, tab2, tab3, tab4 = st.tabs(["📅 行程", "🗺️ 地圖", "🎒 清單", "ℹ️ 資訊"])

with tab1:
    # (這裡放入原本的行程規劃程式碼，為確保運作我簡化示意，請將您原本的 tab1 邏輯貼回此處)
    # 確保使用 selected_day_num 與 current_theme['text'] 等變數
    selected_day_num = st.radio("DaySelect", list(range(1, st.session_state.trip_days_count + 1)), horizontal=True, label_visibility="collapsed", format_func=lambda x: f"Day\n{x}")
    
    # 範例卡片
    st.markdown(f"<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    items = st.session_state.trip_data.get(selected_day_num, [])
    
    # 編輯模式開關
    is_edit_mode = st.toggle("編輯模式")
    if is_edit_mode and st.button("➕ 新增行程", use_container_width=True):
        items.append({"id": int(time.time()), "time":"09:00", "title":"新行程", "loc":"", "cost":0, "cat":"spot", "note":"", "expenses":[]})
        
    # 顯示行程 (使用前面的 CSS class)
    st.markdown('<div class="timeline-wrapper">', unsafe_allow_html=True)
    for item in items:
        # ... (請貼回原本生成 card_html 的邏輯)
        # 這裡僅作示意
        st.markdown(f"""
        <div style="position:relative;">
            <div class="time-label">{item['time']}</div>
            <div class="time-dot"></div>
            <div class="itinerary-card">
                <div class="card-title">{item['title']}</div>
                <div class="card-sub">📍 {item['loc']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.info("地圖功能區") # 請貼回原本 tab2 代碼

with tab3:
    st.info("行李清單區") # 請貼回原本 tab3 代碼

with tab4:
    st.info("航班住宿資訊") # 請貼回原本 tab4 代碼