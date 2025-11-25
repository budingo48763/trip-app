import streamlit as st
from datetime import datetime, timedelta
import random
import urllib.parse

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="2026 阪京之旅", page_icon="⛩️", layout="centered", initial_sidebar_state="collapsed")

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

# 新增許願地點的回調函數
def add_wish_callback():
    name = st.session_state.get("wish_name", "")
    note = st.session_state.get("wish_note", "")
    cat = st.session_state.get("wish_cat", "spot")
    
    if name:
        new_id = int(datetime.now().timestamp())
        st.session_state.wishlist.append({
            "id": new_id,
            "title": name,
            "note": note,
            "cat": cat,
            "added_by": "User", # 之後可改為使用者名稱
            "created_at": datetime.now().strftime("%Y-%m-%d")
        })
        # 清空輸入
        st.session_state.wish_name = ""
        st.session_state.wish_note = ""

# 將許願移動到正式行程
def move_wish_to_plan(wish_item, target_day, target_time):
    new_item = {
        "id": wish_item["id"],
        "time": target_time.strftime("%H:%M"),
        "title": wish_item["title"],
        "loc": wish_item["title"], # 預設地點同標題
        "cost": 0,
        "cat": wish_item["cat"],
        "note": wish_item["note"],
        "expenses": []
    }
    st.session_state.trip_data[target_day].append(new_item)
    # 從許願清單移除
    st.session_state.wishlist = [w for w in st.session_state.wishlist if w['id'] != wish_item['id']]

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

def get_category_icon(cat):
    icons = {
        "trans": "🚃", "food": "🍱", "stay": "♨️", 
        "spot": "⛩️", "shop": "🛍️", "other": "📍"
    }
    return icons.get(cat, "📍")

# -------------------------------------
# 3. CSS 樣式 (新增許願清單樣式)
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
    .price-twd { font-size: 0.75rem; color: rgba(255,255,255,0.8); margin-left: 4px; font-weight: normal;}
    .weather-tag { position: absolute; top: 15px; right: 15px; background: #FDFCF5; padding: 2px 6px; border-radius: 4px; font-weight:bold; color:#555;}
    .card-loc { margin-top: 5px; }
    .card-loc a { color: #8E2F2F; text-decoration: none; border-bottom: 1px solid #8E2F2F; font-weight: bold;}
    .card-note { margin-top: 8px; color: #666; font-size: 0.9rem; font-style: italic; background: #F7F7F7; padding: 5px 10px; border-radius: 4px;}
    .card-time { font-family: 'Noto Serif JP', serif; font-size: 1.8rem; font-weight: 700; color: #2B2B2B; text-align: right; margin-top: 10px;}
    
    .retro-title { font-size: 2.5rem; color: #8E2F2F; text-align: center; font-weight: 900; letter-spacing: 2px; margin-top: 10px;}
    .retro-subtitle { font-size: 0.9rem; color: #888; text-align: center; margin-bottom: 10px; }
    
    /* 封面圖樣式 */
    .cover-image {
        width: 100%; height: 180px; object-fit: cover; border-radius: 0 0 20px 20px;
        margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        background-image: url('https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=2070&auto=format&fit=crop');
        background-size: cover; background-position: center;
        display: flex; align-items: flex-end; justify-content: flex-start; padding: 20px;
    }
    .cover-text {
        color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.8); font-family: 'Noto Serif JP';
    }
    .cover-h1 { font-size: 2rem; font-weight: 900; margin: 0; line-height: 1.2; }
    .cover-p { font-size: 1rem; font-weight: bold; margin: 0; opacity: 0.9; }

    /* 許願清單樣式 */
    .wish-banner {
        background-color: #D4AF37; /* 復古金黃色 */
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(212, 175, 55, 0.3);
    }
    .wish-banner::after {
        content: '✿'; position: absolute; right: -20px; bottom: -30px;
        font-size: 150px; color: rgba(255,255,255,0.2); font-weight: bold;
    }
    .wish-title { font-size: 1.5rem; font-weight: 900; margin-bottom: 5px; display: flex; align-items: center; gap: 10px;}
    .wish-desc { font-size: 0.9rem; opacity: 0.9; }

    /* 虛線新增按鈕 */
    .add-wish-btn {
        border: 2px dashed #D4AF37;
        border-radius: 15px;
        color: #D4AF37;
        text-align: center;
        padding: 15px;
        font-weight: bold;
        cursor: pointer;
        background: rgba(212, 175, 55, 0.05);
        margin-bottom: 20px;
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
    st.session_state.trip_title = "2026 阪京之旅"

if "exchange_rate" not in st.session_state:
    st.session_state.exchange_rate = 0.215

# 初始化許願清單
if "wishlist" not in st.session_state:
    st.session_state.wishlist = [
        {"id": 901, "title": "清水寺", "note": "穿和服拍照", "cat": "spot", "added_by": "User", "created_at": "2025-11-24"},
        {"id": 902, "title": "敘敘苑燒肉", "note": "一定要訂位", "cat": "food", "added_by": "User", "created_at": "2025-11-24"}
    ]

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

for day, items in st.session_state.trip_data.items():
    for item in items:
        if "cat" not in item: item["cat"] = "other"

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

# 頂部封面圖模擬
st.markdown(f"""
<div class="cover-image">
    <div class="cover-text">
        <div class="cover-h1">{st.session_state.trip_title}</div>
        <div class="cover-p">1/17 - 1/22</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("⚙️ 旅程設定 (匯率/標題)"):
    st.session_state.trip_title = st.text_input("旅程標題", value=st.session_state.trip_title)
    c_set1, c_set2 = st.columns(2)
    with c_set1:
        start_date = st.date_input("出發日期", value=datetime.today())
    with c_set2:
        st.session_state.exchange_rate = st.number_input("匯率", value=st.session_state.exchange_rate, step=0.001, format="%.3f")
    trip_days_count = st.number_input("旅遊天數", 1, 30, 5)

for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

tab1, tab2, tab3, tab4 = st.tabs(["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單", "💖 許願清單"])

# ==========================================
# 1. 行程規劃
# ==========================================
with tab1:
    selected_day_num = st.radio("DaySelect", list(range(1, trip_days_count + 1)), index=0, horizontal=False, label_visibility="collapsed", format_func=lambda x: f"Day\n{x}")
    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]
    current_items = st.session_state.trip_data[selected_day_num]
    
    c_date, c_edit = st.columns([2, 1])
    with c_date: st.markdown(f"### 🗓️ {date_str} {week_str}")
    with c_edit: is_edit_mode = st.toggle("✏️ 編輯", value=False)

    total_cost = sum(i['cost'] for i in current_items)
    total_cost_twd = int(total_cost * st.session_state.exchange_rate)
    st.markdown(f"<div style='text-align:right; font-weight:bold; margin-bottom:15px;'><span style='color:#8E2F2F; font-size:1.2rem;'>¥{total_cost:,}</span><span style='color:#999; font-size:0.9rem; margin-left:5px;'>(約 NT${total_cost_twd:,})</span></div>", unsafe_allow_html=True)

    if is_edit_mode:
        if st.button("➕ 新增行程", type="primary", use_container_width=True):
            st.session_state.trip_data[selected_day_num].append({"id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": "", "expenses": []})
            st.rerun()

    st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)
    current_items.sort(key=lambda x: x['time'])
    
    if not current_items: st.info("🍵 目前無行程，請點擊上方「✏️ 編輯」開始規劃。")

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
                    
                    item_twd = int(item['cost'] * st.session_state.exchange_rate)
                    c2.markdown(f"**💰 ¥{item['cost']:,}** <span style='font-size:0.8rem; color:#666'>(NT${item_twd:,})</span>", unsafe_allow_html=True)
                    
                    item['cat'] = st.selectbox("分類", ["trans", "food", "stay", "spot", "shop", "other"], index=["trans", "food", "stay", "spot", "shop", "other"].index(item.get('cat', 'other')), key=f"cat_{item['id']}")
                    item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                    item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                    st.markdown("---")
                    st.caption("🧾 消費明細")
                    if item["expenses"]:
                        for idx, exp in enumerate(item["expenses"]):
                            ce1, ce2, ce3 = st.columns([3, 2, 1])
                            exp_twd = int(exp['price'] * st.session_state.exchange_rate)
                            ce1.text(f"{exp['name']}")
                            ce2.text(f"¥{exp['price']:,} ({exp_twd})")
                            if ce3.button("✖", key=f"d_exp_{item['id']}_{idx}"):
                                item["expenses"].pop(idx)
                                item['cost'] = sum(x['price'] for x in item['expenses'])
                                st.rerun()
                    c_add1, c_add2, c_add3 = st.columns([3, 2, 1])
                    with c_add1: st.text_input("項目", key=f"nm_{item['id']}", label_visibility="collapsed")
                    with c_add2: st.number_input("金額", key=f"pr_{item['id']}", min_value=0, step=100, label_visibility="collapsed")
                    with c_add3: st.button("➕", key=f"add_{item['id']}", on_click=add_expense_callback, args=(item, f"nm_{item['id']}", f"pr_{item['id']}"))
            else:
                h = []
                h.append("<div class='trip-card'>")
                if item['loc']:
                    w_icon, w_temp = get_mock_weather(item['loc'], date_str)
                    h.append(f"<div class='weather-tag'>{w_icon} {w_temp}</div>")
                h.append("<div class='card-header'><div class='card-title-group'>")
                h.append(f"<div class='card-title'>{item['title']}</div>")
                if item['cost'] > 0:
                    card_twd = int(item['cost'] * st.session_state.exchange_rate)
                    h.append(f"<div class='card-price'>¥{item['cost']:,}<span class='price-twd'>(NT${card_twd:,})</span></div>")
                h.append("</div></div>")
                if item['loc']:
                    safe_loc = urllib.parse.quote(item['loc'])
                    h.append(f"<div class='card-loc'>📍 <a href='https://www.google.com/maps/search/?api=1&query={safe_loc}' target='_blank'>{item['loc']}</a></div>")
                note_text = item['note']
                exp_html = ""
                if item['expenses']:
                    for e in item['expenses']:
                        e_twd = int(e['price'] * st.session_state.exchange_rate)
                        exp_html += f"<div style='display:flex; justify-content:space-between;'><span>• {e['name']}</span><span>¥{e['price']:,} <span style='color:#999; font-size:0.75rem'>(NT${e_twd:,})</span></span></div>"
                if note_text or exp_html:
                    h.append(f"<div class='card-note'>{note_text}")
                    if exp_html: h.append(f"<div style='margin-top:8px; padding-top:8px; border-top:1px dashed #ccc; font-size:0.85rem; color:#555;'>{exp_html}</div>")
                    h.append("</div>")
                h.append("</div>")
                st.markdown("".join(h), unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)
    if current_items:
        st.markdown("---")
        route_url = generate_google_map_route(current_items)
        st.markdown(f"<div style='text-align:center;'><a href='{route_url}' target='_blank' style='background:#8E2F2F; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 Google Maps 路線導航</a></div>", unsafe_allow_html=True)

# ==========================================
# 2. 路線全覽
# ==========================================
with tab2:
    st.markdown('<div class="retro-subtitle">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
    map_day = st.selectbox("選擇天數", list(range(1, trip_days_count + 1)), format_func=lambda x: f"Day {x}")
    map_items = st.session_state.trip_data[map_day]
    map_items.sort(key=lambda x: x['time'])
    
    if len(map_items) > 0:
        t_html = []
        t_html.append('<div class="timeline-container">')
        for item in map_items:
            icon = get_category_icon(item.get('cat', 'other'))
            loc_text = f"📍 {item['loc']}" if item['loc'] else ""
            t_html.append(f"<div class='timeline-item'><div class='timeline-icon'>{icon}</div><div class='timeline-content'><div class='tl-time'>{item['time']}</div><div class='tl-title'>{item['title']}</div><div class='tl-loc'>{loc_text}</div></div></div>")
        t_html.append('</div>')
        st.markdown("".join(t_html), unsafe_allow_html=True)
    else:
        st.info("🌸 本日尚無行程。")

# ==========================================
# 3. 準備清單
# ==========================================
with tab3:
    st.markdown('<div class="retro-subtitle">CHECKLIST & TIPS</div>', unsafe_allow_html=True)
    try:
        for category, items in st.session_state.checklist.items():
            with st.expander(f"📌 {category}", expanded=False):
                cols = st.columns(2)
                for i, (item_name, checked) in enumerate(items.items()):
                    st.session_state.checklist[category][item_name] = cols[i % 2].checkbox(item_name, value=checked)
    except:
        st.session_state.checklist = default_checklist
        st.rerun()

# ==========================================
# 4. 💖 許願清單 (仿圖功能)
# ==========================================
with tab4:
    # 黃色 Banner 區塊
    st.markdown("""
    <div class="wish-banner">
        <div class="wish-title">♡ 收藏清單</div>
        <div class="wish-desc">收錄想去的京都角落，與心愛的人共享。</div>
    </div>
    """, unsafe_allow_html=True)

    # 虛線新增按鈕 (使用 Expander 模擬)
    with st.expander("＋ 新增許願地點"):
        c_w1, c_w2 = st.columns([3, 2])
        with c_w1:
            st.text_input("地點名稱", key="wish_name", placeholder="例：金閣寺")
        with c_w2:
            st.selectbox("分類", ["spot", "food", "shop", "stay"], format_func=lambda x: {"spot":"⛩️ 景點", "food":"🍱 美食", "shop":"🛍️ 購物", "stay":"♨️ 住宿"}[x], key="wish_cat")
        st.text_area("備註 (例如：營業時間、必吃)", key="wish_note", placeholder="週三公休，抹茶冰淇淋必點")
        if st.button("加入收藏", type="primary", use_container_width=True):
            add_wish_callback()
            st.rerun()

    # 顯示收藏卡片
    if not st.session_state.wishlist:
        st.markdown("<div style='text-align:center; color:#999; padding:40px;'>尚未收藏任何地點</div>", unsafe_allow_html=True)
    else:
        for wish in st.session_state.wishlist:
            # 每個卡片
            with st.container(border=True):
                wc1, wc2 = st.columns([4, 1])
                with wc1:
                    icon = get_category_icon(wish['cat'])
                    st.markdown(f"**{icon} {wish['title']}**")
                    if wish['note']:
                        st.caption(wish['note'])
                with wc2:
                    # 刪除按鈕
                    if st.button("🗑️", key=f"del_wish_{wish['id']}"):
                        st.session_state.wishlist.remove(wish)
                        st.rerun()
                
                # 排入行程功能
                with st.popover("➡️ 排入行程"):
                    target_day = st.selectbox("選擇天數", list(range(1, trip_days_count + 1)), key=f"wd_{wish['id']}", format_func=lambda x: f"Day {x}")
                    target_time = st.time_input("時間", value=datetime.strptime("10:00", "%H:%M").time(), key=f"wt_{wish['id']}")
                    if st.button("確定移動", key=f"move_{wish['id']}", type="primary"):
                        move_wish_to_plan(wish, target_day, target_time)
                        st.rerun()

    # 底部說明
    st.divider()
    st.info("""
    ℹ️ **如何多人共用？**
    Streamlit 預設是單機模式。若要多人共用此清單，您需要將程式碼連接到 **Google Sheets** 資料庫。
    
    **簡單實作法：**
    1. 在 Streamlit Cloud 設定 `secrets.toml` 放入 Google Sheets API 金鑰。
    2. 將 `st.session_state.wishlist` 的讀取與寫入改為 `conn.read()` 與 `conn.write()`。
    """)