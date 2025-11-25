import streamlit as st
from datetime import datetime, timedelta
import random
import urllib.parse

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="旅日計畫書", page_icon="⛩️", layout="centered", initial_sidebar_state="collapsed")

# -------------------------------------
# 2. 核心功能函數
# -------------------------------------

def add_expense_callback(item, name_key, price_key):
    new_name = st.session_state.get(name_key, "")
    new_price = st.session_state.get(price_key, 0)
    if new_name:
        item["expenses"].append({"name": new_name, "price": new_price})
        item['cost'] = sum(x['price'] for x in item['expenses'])
        st.session_state[name_key] = ""
        st.session_state[price_key] = 0

def get_mock_weather(location, date_str):
    if not location: return "", ""
    seed_str = location + date_str
    seed_val = sum(ord(c) for c in seed_str) 
    random.seed(seed_val)
    weathers = ["☀️ 晴", "⛅ 多雲", "🌧️ 雨", "⛈️ 雷雨", "❄️ 雪"]
    icons = {"☀️ 晴": (15, 25), "⛅ 多雲": (10, 20), "🌧️ 雨": (10, 18), "⛈️ 雷雨": (15, 22), "❄️ 雪": (-5, 5)}
    w = random.choice(weathers)
    temp_range = icons[w]
    t = random.randint(temp_range[0], temp_range[1])
    return w, f"{t}°C"

def generate_google_map_route(items):
    if len(items) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    locations = [urllib.parse.quote(item['loc']) for item in items if item['loc']]
    return base_url + "/".join(locations) if locations else "#"

# 根據分類回傳對應的日式 Emoji
def get_category_icon(cat):
    icons = {
        "trans": "🚃", # 交通
        "food": "🍱",  # 美食
        "stay": "♨️",  # 住宿
        "spot": "⛩️",  # 景點
        "shop": "🛍️",  # 購物
        "other": "📍"  # 其他
    }
    return icons.get(cat, "📍")

# -------------------------------------
# 3. CSS 樣式 (含動態時間軸)
# -------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important;
        color: #2B2B2B !important; 
        font-family: 'Noto Serif JP', 'Times New Roman', serif !important;
    }

    /* 隱藏多餘介面 */
    [data-testid="stSidebarCollapsedControl"], section[data-testid="stSidebar"], 
    div[data-testid="stToolbar"], div[data-testid="stDecoration"], footer {
        display: none !important;
    }
    header[data-testid="stHeader"] { height: 0 !important; background: transparent !important; }

    /* 分頁樣式 */
    button[data-baseweb="tab"] {
        font-family: 'Noto Serif JP', serif !important;
        font-size: 1.0rem !important;
        color: #888 !important;
        border-bottom: 2px solid transparent !important;
        background: transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #8E2F2F !important;
        border-bottom: 3px solid #8E2F2F !important;
        font-weight: bold !important;
    }
    div[data-baseweb="tab-highlight"] { display: none !important; }
    div[data-baseweb="tab-list"] { gap: 5px; border-bottom: 1px solid #ddd; margin-bottom: 15px; }

    /* Day 按鈕橫向排列 */
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
    div[role="radiogroup"] label p::first-line {
        font-size: 0.8rem !important; color: #AAA !important; font-weight: 400 !important; line-height: 1.5 !important;
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #8E2F2F !important; border: 1px solid #8E2F2F !important;
        box-shadow: 0 4px 8px rgba(142, 47, 47, 0.3) !important; transform: translateY(-2px);
    }
    div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }
    div[role="radiogroup"] label[data-checked="true"] p::first-line { color: rgba(255, 255, 255, 0.8) !important; }

    /* 卡片樣式 */
    .trip-card {
        background: #FFFFFF; border: 1px solid #EBE6DE; border-left: 6px solid #8E2F2F;
        padding: 15px 20px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(142, 47, 47, 0.05); position: relative; 
    }
    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; padding-right: 60px; }
    .card-title-group { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .card-title { font-size: 1.3rem; font-weight: 900; color: #2B2B2B; margin: 0; }
    .card-price { background: #8E2F2F; color: white; padding: 3px 8px; font-size: 0.85rem; border-radius: 4px; font-weight: bold; white-space: nowrap; }
    .weather-tag { position: absolute; top: 15px; right: 15px; background: #FDFCF5; padding: 2px 6px; border-radius: 4px; font-weight:bold; color:#555;}
    .card-loc { margin-top: 5px; }
    .card-loc a { color: #8E2F2F; text-decoration: none; border-bottom: 1px solid #8E2F2F; font-weight: bold;}
    .card-note { margin-top: 8px; color: #666; font-size: 0.9rem; font-style: italic; background: #F7F7F7; padding: 5px 10px; border-radius: 4px;}
    .card-time { font-family: 'Noto Serif JP', serif; font-size: 1.8rem; font-weight: 700; color: #2B2B2B; text-align: right; margin-top: 10px;}
    
    .retro-title { font-size: 2.5rem; color: #8E2F2F; text-align: center; font-weight: 900; letter-spacing: 2px; margin-top: 10px;}
    .retro-subtitle { font-size: 0.9rem; color: #888; text-align: center; margin-bottom: 10px; }
    
    /* =========================================
       🎨 動態日式時間軸 CSS
       ========================================= */
    .timeline-container {
        position: relative;
        max-width: 100%;
        margin: 20px auto;
        padding-left: 30px; /* 留空間給左邊的線 */
    }
    
    /* 垂直虛線 */
    .timeline-container::before {
        content: '';
        position: absolute;
        top: 0;
        bottom: 0;
        left: 14px; /* 線的位置 */
        width: 2px;
        background-image: linear-gradient(#8E2F2F 40%, rgba(255,255,255,0) 0%);
        background-position: right;
        background-size: 2px 12px; /* 虛線間距 */
        background-repeat: repeat-y;
    }

    .timeline-item {
        position: relative;
        margin-bottom: 25px;
        animation: fadeInUp 0.6s ease-in-out both; /* 動畫 */
    }
    
    /* 為每個項目增加延遲，製造依序出現的效果 */
    .timeline-item:nth-child(1) { animation-delay: 0.1s; }
    .timeline-item:nth-child(2) { animation-delay: 0.2s; }
    .timeline-item:nth-child(3) { animation-delay: 0.3s; }
    .timeline-item:nth-child(4) { animation-delay: 0.4s; }
    .timeline-item:nth-child(5) { animation-delay: 0.5s; }
    .timeline-item:nth-child(6) { animation-delay: 0.6s; }
    .timeline-item:nth-child(7) { animation-delay: 0.7s; }
    .timeline-item:nth-child(8) { animation-delay: 0.8s; }

    /* 圓形圖標 */
    .timeline-icon {
        position: absolute;
        left: -31px; /* 調整到線的中間 */
        top: 0px;
        width: 32px;
        height: 32px;
        background: #FFFFFF;
        border: 2px solid #8E2F2F;
        border-radius: 50%;
        text-align: center;
        line-height: 28px;
        font-size: 16px;
        z-index: 2;
        box-shadow: 0 2px 4px rgba(142, 47, 47, 0.2);
    }

    /* 內容卡片 */
    .timeline-content {
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-left: 4px solid #8E2F2F;
        padding: 12px 15px;
        border-radius: 4px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }

    .timeline-content:hover {
        transform: scale(1.02); /* 滑鼠懸停放大 */
        box-shadow: 0 5px 12px rgba(142, 47, 47, 0.15);
    }

    .tl-time { font-weight: 700; color: #8E2F2F; font-size: 1.1rem; font-family: 'Noto Serif JP', serif; }
    .tl-title { font-weight: 900; color: #2B2B2B; font-size: 1.05rem; margin-top: 2px; }
    .tl-loc { font-size: 0.85rem; color: #666; margin-top: 4px; display: flex; align-items: center; gap: 4px;}

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translate3d(0, 20px, 0);
        }
        to {
            opacity: 1;
            transform: translate3d(0, 0, 0);
        }
    }

    /* 其他 UI */
    div[data-baseweb="input"], div[data-baseweb="base-input"] { border: none !important; border-bottom: 2px solid #8E2F2F !important; background: transparent !important; }
    input { font-weight: bold !important; color: #2B2B2B !important; }
    div[data-testid="stToggle"] { justify-content: flex-end; padding: 5px; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 4. 資料初始化
# -------------------------------------
if "trip_title" not in st.session_state:
    st.session_state.trip_title = "長野・名古屋"

# 更新資料結構：確保每個項目都有 'cat' (分類)
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id": 101, "time": "11:35", "title": "抵達名古屋", "loc": "中部國際機場", "cost": 0, "cat": "trans", "note": "", "expenses": []}],
        2: [
            {"id": 201, "time": "07:00", "title": "起床 & 早餐", "loc": "相鐵FRESA INN", "cost": 0, "cat": "stay", "note": "晨跑", "expenses": []},
            {"id": 202, "time": "08:00", "title": "移動：名古屋 → 上諏訪", "loc": "JR 特急 (信濃號)", "cost": 0, "cat": "trans", "note": "指定席", "expenses": []},
            {"id": 203, "time": "10:30", "title": "放行李", "loc": "ホテル紅や", "cost": 0, "cat": "stay", "note": "寄放行李", "expenses": []},
            {"id": 204, "time": "11:30", "title": "午餐：鰻魚飯", "loc": "ねばし (古名店)", "cost": 2000, "cat": "food", "note": "排隊美食", "expenses": [{"name": "鰻魚定食", "price": 2000}]},
        ]
    }

# 自動修復與補齊 'cat' 欄位
for day, items in st.session_state.trip_data.items():
    for item in items:
        if "cat" not in item:
            item["cat"] = "other"

# 預設清單
default_checklist = {
    "必要證件": {"護照 (效期6個月以上)": False, "機票證明": False, "Visit Japan Web": False, "日幣現金": False, "信用卡 (JCB/Visa)": False, "海外提款卡": False},
    "電子產品": {"手機 & 充電線": False, "行動電源": False, "SIM卡 / Wifi機": False, "轉接頭 (日本雙孔扁插)": False, "耳機": False},
    "衣物穿搭": {"換洗衣物": False, "睡衣": False, "好走的鞋子": False, "外套 (視季節)": False, "貼身衣物": False},
    "生活用品": {"牙刷牙膏": False, "保養品/化妝品": False, "常備藥 (感冒/腸胃)": False, "塑膠袋 (裝髒衣)": False, "折疊傘": False}
}
if "checklist" not in st.session_state or not isinstance(st.session_state.checklist.get("必要證件"), dict):
    st.session_state.checklist = default_checklist

# -------------------------------------
# 5. 主畫面
# -------------------------------------
st.markdown(f'<div class="retro-title">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown('<div class="retro-subtitle">CLASSIC TRIP PLANNER</div>', unsafe_allow_html=True)

with st.expander("⚙️ 旅程設定"):
    st.session_state.trip_title = st.text_input("旅程標題", value=st.session_state.trip_title)
    start_date = st.date_input("出發日期", value=datetime.today())
    trip_days_count = st.number_input("旅遊天數", 1, 30, 5)

for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

tab1, tab2, tab3 = st.tabs(["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單"])

# ==========================================
# 1. 行程規劃
# ==========================================
with tab1:
    selected_day_num = st.radio(
        "DaySelect", list(range(1, trip_days_count + 1)), 
        index=0, horizontal=False, label_visibility="collapsed",
        format_func=lambda x: f"Day\n{x}" 
    )

    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]

    current_items = st.session_state.trip_data[selected_day_num]
    for item in current_items:
        if "expenses" not in item: item["expenses"] = []
    
    total_cost = sum(i['cost'] for i in current_items)
    
    c_date, c_edit = st.columns([2, 1])
    with c_date:
        st.markdown(f"### 🗓️ {date_str} {week_str}")
    with c_edit:
        is_edit_mode = st.toggle("✏️ 編輯", value=False)

    st.markdown(f"<div style='text-align:right; color:#8E2F2F; font-weight:bold; padding-top:5px; margin-bottom:15px;'>本日預算 ¥{total_cost:,}</div>", unsafe_allow_html=True)

    if is_edit_mode:
        if st.button("➕ 新增行程", type="primary", use_container_width=True):
            st.session_state.trip_data[selected_day_num].append({
                "id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": "", "expenses": []
            })
            st.rerun()

    st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)
    current_items.sort(key=lambda x: x['time'])
    
    if not current_items:
        st.info("🍵 目前無行程，請點擊上方「✏️ 編輯」開始規劃。")

    for index, item in enumerate(current_items):
        c_time, c_card = st.columns([1.2, 4])
        
        with c_time:
            st.markdown(f"<div class='card-time'>{item['time']}</div>", unsafe_allow_html=True)
            st.markdown("<div style='float:right; margin-right:-26px; margin-top:-25px; width:12px; height:12px; background:#8E2F2F; border-radius:50%; position:relative; z-index:2; border:2px solid #FDFCF5;'></div>", unsafe_allow_html=True)

        with c_card:
            if is_edit_mode:
                with st.expander(f"📝 {item['title']}", expanded=True):
                    c_del_btn, c_title_input = st.columns([1, 5])
                    if c_del_btn.button("🗑️", key=f"d_{item['id']}"):
                        st.session_state.trip_data[selected_day_num].pop(index)
                        st.rerun()
                    item['title'] = c_title_input.text_input("標題", item['title'], key=f"t_{item['id']}", label_visibility="collapsed")
                    
                    c1, c2 = st.columns(2)
                    try: t_obj = datetime.strptime(item['time'], "%H:%M").time()
                    except: t_obj = datetime.strptime("09:00", "%H:%M").time()
                    item['time'] = c1.time_input("時間", value=t_obj, key=f"tm_{item['id']}").strftime("%H:%M")
                    c2.markdown(f"**💰 ¥{item['cost']:,}**")
                    
                    # 分類選單 (編輯模式下選擇)
                    item['cat'] = st.selectbox("分類", ["trans", "food", "stay", "spot", "shop", "other"], 
                                               index=["trans", "food", "stay", "spot", "shop", "other"].index(item.get('cat', 'other')),
                                               format_func=lambda x: {"trans":"🚃 交通", "food":"🍱 美食", "stay":"♨️ 住宿", "spot":"⛩️ 景點", "shop":"🛍️ 購物", "other":"📍 其他"}[x],
                                               key=f"cat_{item['id']}")
                    
                    item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                    item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                    
                    st.markdown("---")
                    st.caption("🧾 消費明細")
                    if item["expenses"]:
                        for idx, exp in enumerate(item["expenses"]):
                            ce1, ce2, ce3 = st.columns([3, 2, 1])
                            ce1.text(f"{exp['name']}")
                            ce2.text(f"¥{exp['price']:,}")
                            if ce3.button("✖", key=f"d_exp_{item['id']}_{idx}"):
                                item["expenses"].pop(idx)
                                item['cost'] = sum(x['price'] for x in item['expenses'])
                                st.rerun()
                    
                    c_add1, c_add2, c_add3 = st.columns([3, 2, 1])
                    with c_add1: st.text_input("項目", key=f"nm_{item['id']}", label_visibility="collapsed")
                    with c_add2: st.number_input("金額", key=f"pr_{item['id']}", min_value=0, step=100, label_visibility="collapsed")
                    with c_add3: st.button("➕", key=f"add_{item['id']}", on_click=add_expense_callback, args=(item, f"nm_{item['id']}", f"pr_{item['id']}"))
            else:
                # 瀏覽模式
                weather_html = ""
                if item['loc']:
                    w_icon, w_temp = get_mock_weather(item['loc'], date_str)
                    weather_html = f"<div class='weather-tag'>{w_icon} {w_temp}</div>"

                price_html = ""
                if item['cost'] > 0:
                    price_html = f"<div class='card-price'>¥{item['cost']:,}</div>"
                
                loc_html = ""
                if item['loc']:
                    safe_loc_query = urllib.parse.quote(item['loc'])
                    loc_html = f"<div class='card-loc'>📍 <a href='https://www.google.com/maps/search/?api=1&query={safe_loc_query}' target='_blank'>{item['loc']}</a></div>"

                note_html = ""
                note_content = item['note']
                if item['expenses']:
                    exp_list = "".join([f"<div style='display:flex; justify-content:space-between;'><span>• {e['name']}</span><span>¥{e['price']:,}</span></div>" for e in item['expenses']])
                    note_content += f"<div style='margin-top:8px; padding-top:8px; border-top:1px dashed #ccc; font-size:0.85rem; color:#555;'>{exp_list}</div>"
                
                if note_content:
                    note_html = f"<div class='card-note'>{note_content}</div>"

                # HTML 單行串接
                card_html = f"<div class='trip-card'>{weather_html}<div class='card-header'><div class='card-title-group'><div class='card-title'>{item['title']}</div>{price_html}</div></div>{loc_html}{note_html}</div>"
                st.markdown(card_html, unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)
    if current_items:
        st.markdown("---")
        route_url = generate_google_map_route(current_items)
        st.markdown(f"<div style='text-align:center;'><a href='{route_url}' target='_blank' style='background:#8E2F2F; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 Google Maps 路線導航</a></div>", unsafe_allow_html=True)

# ==========================================
# 2. 路線全覽 (全新動態日式風格)
# ==========================================
with tab2:
    st.markdown('<div class="retro-subtitle">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
    map_day = st.selectbox("選擇天數", list(range(1, trip_days_count + 1)), format_func=lambda x: f"Day {x}")
    map_items = st.session_state.trip_data[map_day]
    map_items.sort(key=lambda x: x['time'])
    
    if len(map_items) > 0:
        # 組合 HTML 結構
        timeline_html = '<div class="timeline-container">'
        
        for item in map_items:
            icon = get_category_icon(item.get('cat', 'other'))
            loc_text = f"📍 {item['loc']}" if item['loc'] else ""
            
            # 單行 HTML 避免縮排問題
            timeline_html += f"""
            <div class="timeline-item">
                <div class="t
