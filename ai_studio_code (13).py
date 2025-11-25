import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import math
import pandas as pd  # 新增 pandas 用於 Excel 處理

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="2026 阪京之旅", page_icon="⛩️", layout="centered", initial_sidebar_state="collapsed")

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
}

TRANSPORT_OPTIONS = ["🚆 電車", "🚌 巴士", "🚶 步行", "🚕 計程車", "🚗 自駕", "🚢 船"]

def calculate_distance(loc1, loc2):
    coord1 = LOCATION_DB.get(loc1)
    coord2 = LOCATION_DB.get(loc2)
    if not coord1 or not coord2: return 9999 
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def calculate_default_transport(loc_from, loc_to):
    if not loc_from or not loc_to: return "📍 移動", 30
    dist = calculate_distance(loc_from, loc_to)
    if dist == 9999: return "📍 移動", 30 
    if dist < 0.02: return "🚶 步行", int(dist * 1000) + 5
    elif dist < 0.05: return "🚕 計程車", int(dist * 600) + 10
    else: return "🚆 電車", int(dist * 800) + 15

def optimize_route_logic(items):
    if not items: return []
    start_node = items[0]
    unvisited = items[1:]
    sorted_items = [start_node]
    current_node = start_node
    while unvisited:
        nearest_node = min(unvisited, key=lambda x: calculate_distance(current_node['loc'], x['loc']))
        sorted_items.append(nearest_node)
        current_node = nearest_node
        unvisited.remove(nearest_node)
    
    start_time = datetime.strptime("09:00", "%H:%M")
    for i, item in enumerate(sorted_items):
        new_time = start_time + timedelta(hours=2 * i)
        item['time'] = new_time.strftime("%H:%M")
        if i < len(sorted_items) - 1:
            next_item = sorted_items[i+1]
            mode, mins = calculate_default_transport(item['loc'], next_item['loc'])
            item['trans_mode'] = mode
            item['trans_min'] = mins
    return sorted_items

def generate_google_map_route(items):
    if len(items) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    locations = [urllib.parse.quote(item['loc']) for item in items if item['loc']]
    return base_url + "/".join(locations) if locations else "#"

def get_category_icon(cat):
    icons = {"trans": "🚃", "food": "🍱", "stay": "🏨", "spot": "⛩️", "shop": "🛍️", "other": "📍"}
    return icons.get(cat, "📍")

# Excel 匯入處理函數
def process_excel_upload(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        # 預期欄位: Day, Time, Title, Location, Cost, Note
        required_cols = ['Day', 'Time', 'Title']
        if not all(col in df.columns for col in required_cols):
            st.error("Excel 格式錯誤：缺少 Day, Time 或 Title 欄位")
            return

        new_trip_data = {}
        
        for _, row in df.iterrows():
            day = int(row['Day'])
            if day not in new_trip_data: new_trip_data[day] = []
            
            # 處理時間格式
            time_val = row['Time']
            if isinstance(time_val, str):
                time_str = time_val
            elif isinstance(time_val, (datetime, pd.Timestamp)): # 修正: 檢查是否為 Timestamp
                time_str = time_val.strftime("%H:%M")
            else:
                time_str = "09:00"

            item = {
                "id": int(time.time() * 1000) + _, # 避免 ID 重複
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
# 3. CSS 樣式
# -------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important;
        color: #2B2B2B !important; 
        font-family: 'Noto Serif JP', 'Times New Roman', serif !important;
    }

    [data-testid="stSidebarCollapsedControl"], section[data-testid="stSidebar"], 
    div[data-testid="stToolbar"], div[data-testid="stDecoration"], footer {
        display: none !important;
    }
    header[data-testid="stHeader"] { height: 0 !important; background: transparent !important; }

    /* Day 按鈕 */
    div[role="radiogroup"] {
        display: flex !important; flex-direction: row !important; overflow-x: auto !important;
        gap: 10px !important; padding: 5px 2px !important; width: 100% !important; justify-content: flex-start !important;
    }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        background-color: #FFFFFF !important; border: 1px solid #E0E0E0 !important;
        min-width: 60px !important; width: 60px !important; height: 75px !important;
        display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important;
        border-radius: 4px !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        margin: 0 !important; padding: 0 !important; cursor: pointer !important;
    }
    div[role="radiogroup"] label p {
        font-family: 'Times New Roman', serif !important; text-align: center !important; width: 100% !important;
        line-height: 1 !important; font-size: 1.8rem !important; font-weight: 500 !important; color: #666 !important; margin: 0 !important;
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #8E2F2F !important; border: 1px solid #8E2F2F !important;
        box-shadow: 0 4px 8px rgba(142, 47, 47, 0.3) !important; transform: translateY(-2px);
    }
    div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }

    /* 行程卡片 */
    .timeline-wrapper { position: relative; padding-left: 20px; }
    .itinerary-card {
        background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px;
        padding: 15px; margin-bottom: 0px; position: relative;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); z-index: 2;
    }
    .time-dot {
        position: absolute; left: -26px; top: 20px; width: 12px; height: 12px;
        background-color: #333; border-radius: 50%; z-index: 2; border: 2px solid #FDFCF5;
    }
    .time-label {
        position: absolute; left: -70px; top: 15px; font-size: 0.85rem;
        font-weight: bold; color: #888; font-family: sans-serif;
    }
    .connector-line {
        border-left: 2px dashed #CCC; margin-left: -21px; padding-left: 21px;
        padding-top: 15px; padding-bottom: 15px; min-height: 40px; position: relative; z-index: 1;
        display: flex; align-items: center;
    }
    .travel-badge {
        background-color: #FFFFFF; border: 1px solid #DDD; border-radius: 6px;
        padding: 5px 10px; display: inline-block; font-size: 0.8rem; color: #555;
        font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-left: 10px;
    }
    .card-title { font-size: 1.2rem; font-weight: 900; color: #2B2B2B; margin-bottom: 4px; }
    .card-sub { font-size: 0.9rem; color: #666; display: flex; align-items: center; gap: 5px; }
    .card-tag { background: #8E2F2F; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: auto;}

    /* 重要資訊卡片 */
    .info-card {
        background-color: #FFFFFF; border-radius: 12px; padding: 20px; margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #F0F0F0;
    }
    .info-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: #888; font-size: 0.85rem; font-weight: bold; }
    .info-time { font-size: 1.8rem; font-weight: 900; color: #2B2B2B; margin-bottom: 5px; font-family: 'Times New Roman', serif; }
    .info-loc { color: #666; font-size: 0.9rem; display: flex; align-items: center; gap: 5px; }
    .info-tag { background: #F4F4F4; color: #666; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
    
    /* 路線全覽動畫 */
    .map-tl-container { position: relative; max-width: 100%; margin: 20px auto; padding-left: 30px; }
    .map-tl-container::before {
        content: ''; position: absolute; top: 0; bottom: 0; left: 14px; width: 2px;
        background-image: linear-gradient(#8E2F2F 40%, rgba(255,255,255,0) 0%);
        background-position: right; background-size: 2px 12px; background-repeat: repeat-y;
    }
    .map-tl-item { position: relative; margin-bottom: 25px; animation: fadeInUp 0.6s ease-in-out both; }
    .map-tl-icon {
        position: absolute; left: -31px; top: 0px; width: 32px; height: 32px;
        background: #FFFFFF; border: 2px solid #8E2F2F; border-radius: 50%;
        text-align: center; line-height: 28px; font-size: 16px; z-index: 2;
        box-shadow: 0 2px 4px rgba(142, 47, 47, 0.2);
    }
    .map-tl-content {
        background: #FFFFFF; border: 1px solid #E0E0E0; border-left: 4px solid #8E2F2F;
        padding: 12px 15px; border-radius: 4px; box-shadow: 0 3px 6px rgba(0,0,0,0.05);
    }
    @keyframes fadeInUp { from { opacity: 0; transform: translate3d(0, 20px, 0); } to { opacity: 1; transform: translate3d(0, 0, 0); } }

    /* UI Tweaks */
    button[data-baseweb="tab"] { color: #888; border-bottom: 2px solid transparent; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #8E2F2F; border-bottom: 3px solid #8E2F2F; font-weight: bold; }
    div[data-baseweb="input"], div[data-baseweb="base-input"] { border: none !important; border-bottom: 2px solid #8E2F2F !important; background: transparent !important; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 4. 資料初始化
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "time": "09:00", "title": "京都車站", "loc": "京都車站", "cost": 0, "cat": "trans", "note": "起點", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30},
            {"id": 102, "time": "12:00", "title": "金閣寺", "loc": "金閣寺", "cost": 400, "cat": "spot", "note": "稍遠", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30},
            {"id": 103, "time": "15:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "cat": "spot", "note": "著名景點", "expenses": [], "trans_mode": "📍 移動", "trans_min": 30}
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
        {"id": 2, "name": "尚未安排住宿", "range": "D4-D6 (3泊)", "date": "1/20 - 1/22", "addr": "大阪市...", "link": "#"}
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
# 5. 主畫面
# -------------------------------------
st.markdown(f'<div style="font-size:2.5rem; font-weight:900; text-align:center; margin-bottom:5px;">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#888; font-size:0.9rem; margin-bottom:20px;">1/17 - 1/22</div>', unsafe_allow_html=True)

# --- Settings Expander (含 Excel 匯入) ---
with st.expander("⚙️ 旅程設定 & 匯入"):
    st.session_state.trip_title = st.text_input("旅程標題", value=st.session_state.trip_title)
    c_set1, c_set2 = st.columns(2)
    with c_set1: start_date = st.date_input("出發日期", value=datetime.today())
    with c_set2: st.session_state.exchange_rate = st.number_input("匯率", value=st.session_state.exchange_rate, step=0.001, format="%.3f")
    st.session_state.trip_days_count = st.number_input("旅遊天數", 1, 30, st.session_state.trip_days_count)
    
    st.markdown("---")
    st.caption("📥 從 Excel 匯入行程 (欄位: Day, Time, Title, Location, Cost, Note)")
    uploaded_file = st.file_uploader("上傳 .xlsx 檔案", type=["xlsx"], label_visibility="collapsed")
    if uploaded_file:
        if st.button("確認匯入"):
            process_excel_upload(uploaded_file)

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

    c_head1, c_head2 = st.columns([2, 1])
    with c_head1:
        st.markdown(f"<div style='font-size:2rem; font-weight:900; font-family:Times New Roman;'>Day {selected_day_num}</div>", unsafe_allow_html=True)
        st.caption(f"{date_str} {week_str}")
    with c_head2:
        if st.button("⚡ AI 順路", use_container_width=True):
            with st.spinner("計算最佳路徑..."):
                time.sleep(0.5)
                st.session_state.trip_data[selected_day_num] = optimize_route_logic(st.session_state.trip_data[selected_day_num])
            st.rerun()

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
        
        # 修正：確保 expenses 欄位存在
        if "expenses" not in item: item["expenses"] = []
        
        # 計算總消費 (如果有明細，以明細為主，否則顯示預算)
        current_expense_sum = sum(x['price'] for x in item['expenses'])
        display_cost = current_expense_sum if current_expense_sum > 0 else item['cost']
        price_tag = f"¥{display_cost:,}" if display_cost > 0 else ""
        
        # 卡片顯示
        card_html = f"""
        <div style="position:relative;">
            <div class="time-label">{item['time']}</div>
            <div class="time-dot"></div>
            <div class="itinerary-card">
                <div class="card-title">{icon} {item['title']}</div>
                <div class="card-sub">
                    <span>📍 {item['loc'] if item['loc'] else '未設定地點'}</span>
                    <span class="card-tag">{price_tag}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # --- 記帳功能回歸 (在卡片下方) ---
        with st.expander(f"💰 記帳與筆記 ({len(item['expenses'])})"):
            if is_edit_mode:
                item['note'] = st.text_area("備註", item['note'], key=f"note_{item['id']}")
            else:
                if item['note']: st.info(item['note'])

            # 顯示現有支出
            for i_exp, exp in enumerate(item['expenses']):
                c_ex1, c_ex2, c_ex3 = st.columns([3, 2, 1])
                c_ex1.text(exp['name'])
                c_ex2.text(f"¥{exp['price']}")
                if is_edit_mode and c_ex3.button("x", key=f"del_exp_{item['id']}_{i_exp}"):
                    item['expenses'].pop(i_exp)
                    st.rerun()
            
            # 新增支出
            c_new1, c_new2, c_new3 = st.columns([3, 2, 1])
            new_exp_name = c_new1.text_input("項目", placeholder="如: 門票", key=f"new_exp_n_{item['id']}", label_visibility="collapsed")
            new_exp_price = c_new2.number_input("金額", min_value=0, step=100, key=f"new_exp_p_{item['id']}", label_visibility="collapsed")
            if c_new3.button("➕", key=f"add_exp_{item['id']}"):
                if new_exp_name and new_exp_price > 0:
                    item['expenses'].append({"name": new_exp_name, "price": new_exp_price})
                    item['cost'] = sum(x['price'] for x in item['expenses']) # 更新總金額
                    st.rerun()

        # 編輯功能
        if is_edit_mode:
            with st.expander(f"設定：{item['title']}", expanded=False):
                c1, c2 = st.columns(2)
                item['title'] = c1.text_input("名稱", item['title'], key=f"t_{item['id']}")
                item['loc'] = c2.text_input("地點", item['loc'], key=f"l_{item['id']}")
                try: t_obj = datetime.strptime(item['time'], "%H:%M").time()
                except: t_obj = datetime.strptime("09:00", "%H:%M").time()
                item['time'] = c1.time_input("時間", value=t_obj, key=f"tm_{item['id']}").strftime("%H:%M")
                item['cost'] = c2.number_input("預算 (無細項時顯示)", value=item['cost'], step=100, key=f"c_{item['id']}")
                if st.button("🗑️ 刪除", key=f"del_{item['id']}"):
                    st.session_state.trip_data[selected_day_num].pop(index)
                    st.rerun()

        # 交通連接線
        if index < len(current_items) - 1:
            if "trans_mode" not in item: item["trans_mode"] = "📍 移動"
            if "trans_min" not in item: item["trans_min"] = 30
            
            if is_edit_mode:
                st.markdown('<div class="connector-line">', unsafe_allow_html=True)
                c_t1, c_t2 = st.columns([2, 1])
                item['trans_mode'] = c_t1.selectbox("交通", TRANSPORT_OPTIONS, index=0 if item['trans_mode'] not in TRANSPORT_OPTIONS else TRANSPORT_OPTIONS.index(item['trans_mode']), key=f"tr_m_{item['id']}", label_visibility="collapsed")
                item['trans_min'] = c_t2.number_input("分", value=item['trans_min'], step=5, key=f"tr_t_{item['id']}", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                travel_info = f"{item['trans_mode']} 約 {item['trans_min']} 分"
                st.markdown(f'<div class="connector-line"><span class="travel-badge">{travel_info}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if current_items:
        st.markdown("---")
        st.markdown(f"<div style='text-align:center;'><a href='{generate_google_map_route(current_items)}' target='_blank' style='background:#333; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 開啟 Google Maps 導航</a></div>", unsafe_allow_html=True)

# ==========================================
# 2. 路線全覽
# ==========================================
with tab2:
    st.markdown('<div class="retro-subtitle" style="font-weight:900; color:#888; text-align:center; margin-bottom:15px; letter-spacing:1px;">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
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
                    <div style='color:#8E2F2F; font-weight:bold;'>{item['time']}</div>
                    <div style='font-weight:900; font-size:1.1rem;'>{item['title']}</div>
                    <div style='font-size:0.85rem; color:#666;'>{loc_text}</div>
                </div>
            </div>""")
        t_html.append('</div>')
        st.markdown("".join(t_html), unsafe_allow_html=True)
    else:
        st.info("🌸 本日尚無行程")

# ==========================================
# 3. 準備清單 (可編輯 + 當地資訊)
# ==========================================
with tab3:
    c_list_head, c_list_edit = st.columns([3, 1])
    c_list_head.markdown("### 🎒 行李檢查表")
    edit_list_mode = c_list_edit.toggle("編輯清單")

    # 顯示/編輯清單
    for category in list(st.session_state.checklist.keys()):
        st.markdown(f"**{category}**")
        items = st.session_state.checklist[category]
        
        # 顯示項目
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
        
        # 執行刪除
        if keys_to_delete:
            for k in keys_to_delete:
                del st.session_state.checklist[category][k]
            st.rerun()

        # 新增項目
        if edit_list_mode:
            new_item = st.text_input(f"新增至 {category}", key=f"new_item_{category}", placeholder="項目名稱")
            if new_item and st.button("加入", key=f"add_btn_{category}"):
                st.session_state.checklist[category][new_item] = False
                st.rerun()
        
        if edit_list_mode and st.button(f"刪除分類 {category}", key=f"del_cat_{category}"):
             del st.session_state.checklist[category]
             st.rerun()

    if edit_list_mode:
        st.markdown("---")
        new_cat = st.text_input("新增分類名稱", placeholder="例如: 攝影器材")
        if new_cat and st.button("新增分類"):
            st.session_state.checklist[new_cat] = {}
            st.rerun()

    current_check = sum([sum(c.values()) for c in st.session_state.checklist.values()])
    total_check = sum([len(c) for c in st.session_state.checklist.values()])
    if total_check > 0:
        st.progress(current_check / total_check)
        st.caption(f"完成度: {current_check} / {total_check}")

    # --- 當地旅遊資訊區塊 ---
    st.markdown("---")
    st.markdown("### 🇯🇵 當地旅遊資訊")
    
    info_cols = st.columns(2)
    with info_cols[0]:
        st.info("**⛅ 氣候 (1月)**\n\n平均氣溫 2°C ~ 9°C，早晚寒冷，建議洋蔥式穿搭，必備大衣與圍巾。")
        st.success("**🔌 電壓**\n\n100V，插座為雙平腳（與台灣相同），大多無需轉接頭，但若有三腳插頭需轉接。")
    with info_cols[1]:
        st.warning("**🚑 緊急電話**\n\n警察局：110\n火警/救護車：119\n外交部駐日代表處：03-3280-7811")
        st.error("**💴 小費與退稅**\n\n日本無小費文化。\n消費滿 ¥5,000 (未稅) 可退稅 10% (需出示護照)。")

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
    
    st.markdown(f"""
    <div class="info-card">
        <div class="info-header"><span>📅 {out_f['date']}</span> <span>✈️ {out_f['code']}</span></div>
        <div class="info-time">{out_f['dep']} -> {out_f['arr']}</div>
        <div class="info-loc"><span>📍 {out_f['dep_loc']}</span> <span style="margin:0 5px;">✈</span> <span>{out_f['arr_loc']}</span></div>
        <div style="text-align:right; margin-top:5px;"><span class="info-tag">去程</span></div>
    </div>""", unsafe_allow_html=True)

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

    st.markdown(f"""
    <div class="info-card">
        <div class="info-header"><span>📅 {in_f['date']}</span> <span>✈️ {in_f['code']}</span></div>
        <div class="info-time">{in_f['dep']} -> {in_f['arr']}</div>
        <div class="info-loc"><span>📍 {in_f['dep_loc']}</span> <span style="margin:0 5px;">✈</span> <span>{in_f['arr_loc']}</span></div>
        <div style="text-align:right; margin-top:5px;"><span class="info-tag">回程</span></div>
    </div>""", unsafe_allow_html=True)

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

        hotel_html = f"""
        <div class="info-card" style="border-left: 5px solid #8E2F2F;">
            <div class="info-header"><span class="info-tag" style="background:#8E2F2F; color:white;">{hotel['range']}</span><span>{hotel['date']}</span></div>
            <div style="font-size:1.3rem; font-weight:900; color:#2B2B2B; margin: 10px 0;">{hotel['name']}</div>
            <div class="info-loc" style="margin-bottom:10px;">📍 {hotel['addr']}</div>
            <a href="{hotel['link']}" target="_blank" style="text-decoration:none; color:#8E2F2F; font-size:0.9rem; font-weight:bold; border:1px solid #8E2F2F; padding:4px 12px; border-radius:20px;">🗺️ 地圖</a>
        </div>"""
        st.markdown(hotel_html, unsafe_allow_html=True)