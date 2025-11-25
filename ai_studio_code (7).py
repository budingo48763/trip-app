import streamlit as st
from datetime import datetime, timedelta
import random
import urllib.parse
import time
import math

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="2026 阪京之旅", page_icon="⛩️", layout="centered", initial_sidebar_state="collapsed")

# -------------------------------------
# 2. 核心功能函數 & AI 演算法
# -------------------------------------

# 🌏 模擬座標資料庫 (AI 順路用)
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

def add_expense_callback(item, name_key, price_key):
    new_name = st.session_state.get(name_key, "")
    new_price = st.session_state.get(price_key, 0)
    if new_name:
        item["expenses"].append({"name": new_name, "price": new_price})
        item['cost'] = sum(x['price'] for x in item['expenses'])
        st.session_state[name_key] = ""
        st.session_state[price_key] = 0

# 計算距離
def calculate_distance(loc1, loc2):
    coord1 = LOCATION_DB.get(loc1)
    coord2 = LOCATION_DB.get(loc2)
    if not coord1 or not coord2: return 9999 
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

# 🔥 AI 最近鄰居排序
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
    return sorted_items

# 模擬交通資訊
def get_travel_info(loc_from, loc_to):
    if not loc_from or not loc_to: return None
    dist = calculate_distance(loc_from, loc_to)
    if dist == 9999: return "📍 移動中"
    if dist < 0.02: return f"🚶 步行 約 {int(dist * 1000)} 分"
    elif dist < 0.05: return f"🚕 計程車 約 {int(dist * 600)} 分"
    else: return f"🚆 電車/巴士 約 {int(dist * 800)} 分"

def generate_google_map_route(items):
    if len(items) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    locations = [urllib.parse.quote(item['loc']) for item in items if item['loc']]
    return base_url + "/".join(locations) if locations else "#"

def get_category_icon(cat):
    icons = {"trans": "🚃", "food": "🍱", "stay": "🏨", "spot": "⛩️", "shop": "🛍️", "other": "📍"}
    return icons.get(cat, "📍")

# -------------------------------------
# 3. CSS 樣式 (完整版)
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

    /* =========================================
       Day 按鈕樣式 (強制橫向)
       ========================================= */
    div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important; /* 關鍵：強制橫向 */
        overflow-x: auto !important;    /* 關鍵：可左右滑動 */
        gap: 10px !important;
        padding: 5px 2px !important;
        width: 100% !important;
        justify-content: flex-start !important;
    }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    
    div[role="radiogroup"] label {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        min-width: 60px !important; 
        width: 60px !important;
        height: 75px !important;
        display: flex !important; 
        flex-direction: column !important;
        align-items: center !important; 
        justify-content: center !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
    }
    div[role="radiogroup"] label p {
        font-family: 'Times New Roman', serif !important;
        text-align: center !important;
        width: 100% !important;
        font-size: 1.8rem !important; 
        font-weight: 500 !important; color: #666 !important;
        margin: 0 !important;
        line-height: 1 !important;
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

    /* =========================================
       垂直時間軸與卡片
       ========================================= */
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
    }
    .travel-badge {
        background-color: #FFFFFF; border: 1px solid #DDD; border-radius: 6px;
        padding: 5px 10px; display: inline-block; font-size: 0.8rem; color: #555;
        font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-left: 10px;
    }
    .card-title { font-size: 1.2rem; font-weight: 900; color: #2B2B2B; margin-bottom: 4px; }
    .card-sub { font-size: 0.9rem; color: #666; display: flex; align-items: center; gap: 5px; }
    .card-tag { background: #8E2F2F; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; margin-left: auto;}

    /* 動態全覽時間軸 */
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

    /* UI 元件微調 */
    button[data-baseweb="tab"] { color: #888; border-bottom: 2px solid transparent; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #8E2F2F; border-bottom: 3px solid #8E2F2F; font-weight: bold; }
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

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "time": "09:00", "title": "京都車站", "loc": "京都車站", "cost": 0, "cat": "trans", "note": "起點", "expenses": []},
            {"id": 102, "time": "12:00", "title": "金閣寺", "loc": "金閣寺", "cost": 400, "cat": "spot", "note": "稍遠", "expenses": []},
            {"id": 103, "time": "15:00", "title": "清水寺", "loc": "清水寺", "cost": 400, "cat": "spot", "note": "著名景點", "expenses": []},
            {"id": 104, "time": "18:00", "title": "八坂神社", "loc": "八坂神社", "cost": 0, "cat": "spot", "note": "離清水寺近", "expenses": []}
        ],
        2: []
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
st.markdown(f'<div style="font-size:2.5rem; font-weight:900; text-align:center; margin-bottom:5px;">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#888; font-size:0.9rem; margin-bottom:20px;">1/17 - 1/22</div>', unsafe_allow_html=True)

with st.expander("⚙️ 旅程設定"):
    st.session_state.trip_title = st.text_input("旅程標題", value=st.session_state.trip_title)
    c_set1, c_set2 = st.columns(2)
    with c_set1: start_date = st.date_input("出發日期", value=datetime.today())
    with c_set2: st.session_state.exchange_rate = st.number_input("匯率", value=st.session_state.exchange_rate, step=0.001, format="%.3f")
    trip_days_count = st.number_input("旅遊天數", 1, 30, 5)

for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

tab1, tab2, tab3 = st.tabs(["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單"])

# ==========================================
# 1. 行程規劃 (AI 順路 + 交通連接)
# ==========================================
with tab1:
    selected_day_num = st.radio("DaySelect", list(range(1, trip_days_count + 1)), index=0, horizontal=False, label_visibility="collapsed", format_func=lambda x: f"Day\n{x}")
    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]
    current_items = st.session_state.trip_data[selected_day_num]

    c_head1, c_head2 = st.columns([2, 1])
    with c_head1:
        st.markdown(f"<div style='font-size:2rem; font-weight:900; font-family:Times New Roman;'>Day {selected_day_num}</div>", unsafe_allow_html=True)
        st.caption(f"{date_str} {week_str}")
    with c_head2:
        if st.button("⚡ AI 順路", use_container_width=True, help="根據地點位置自動排序"):
            with st.spinner("AI 正在計算最佳地理路徑..."):
                time.sleep(1)
                optimized_items = optimize_route_logic(st.session_state.trip_data[selected_day_num])
                st.session_state.trip_data[selected_day_num] = optimized_items
            st.toast("✨ 路線已最佳化！", icon="🗺️")
            st.rerun()

    is_edit_mode = st.toggle("✏️ 編輯模式", value=False)

    if is_edit_mode:
        if st.button("➕ 新增行程", type="primary", use_container_width=True):
            st.session_state.trip_data[selected_day_num].append({"id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": "", "expenses": []})
            st.rerun()

    st.markdown('<div class="timeline-wrapper" style="margin-top:20px;">', unsafe_allow_html=True)
    
    if not current_items:
        st.info("🍵 點擊「編輯模式」開始安排今日行程")

    for index, item in enumerate(current_items):
        icon = get_category_icon(item['cat'])
        price_tag = f"¥{item['cost']:,}" if item['cost'] > 0 else ""
        
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

        if is_edit_mode:
            with st.expander(f"設定：{item['title']}", expanded=False):
                c1, c2 = st.columns(2)
                item['title'] = c1.text_input("名稱", item['title'], key=f"t_{item['id']}")
                try: t_obj = datetime.strptime(item['time'], "%H:%M").time()
                except: t_obj = datetime.strptime("09:00", "%H:%M").time()
                item['time'] = c2.time_input("時間", value=t_obj, key=f"tm_{item['id']}").strftime("%H:%M")
                item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}", placeholder="輸入: 清水寺, 京都車站...")
                item['cost'] = st.number_input("預算 (JPY)", value=item['cost'], step=100, key=f"c_{item['id']}")
                if st.button("🗑️ 刪除", key=f"del_{item['id']}"):
                    st.session_state.trip_data[selected_day_num].pop(index)
                    st.rerun()

        if index < len(current_items) - 1:
            next_item = current_items[index + 1]
            travel_info = get_travel_info(item['loc'], next_item['loc'])
            if not travel_info: travel_info = "🔻 移動中"
            st.markdown(f'<div class="connector-line"><span class="travel-badge">{travel_info}</span></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    if current_items:
        st.markdown("---")
        route_url = generate_google_map_route(current_items)
        st.markdown(f"<div style='text-align:center;'><a href='{route_url}' target='_blank' style='background:#333; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 開啟 Google Maps 導航</a></div>", unsafe_allow_html=True)

# ==========================================
# 2. 路線全覽 (回歸！動態日式地圖)
# ==========================================
with tab2:
    st.markdown('<div class="retro-subtitle">ILLUSTRATED ROUTE MAP</div>', unsafe_allow_html=True)
    map_day = st.selectbox("選擇天數", list(range(1, trip_days_count + 1)), format_func=lambda x: f"Day {x}", key="map_day_select")
    map_items = st.session_state.trip_data[map_day]
    map_items.sort(key=lambda x: x['time'])
    
    if len(map_items) > 0:
        t_html = []
        t_html.append('<div class="map-tl-container">')
        
        for i, item in enumerate(map_items):
            icon = get_category_icon(item.get('cat', 'other'))
            loc_text = f"📍 {item['loc']}" if item['loc'] else ""
            # 增加動畫延遲
            delay = (i + 1) * 0.1
            t_html.append(f"<div class='map-tl-item' style='animation-delay:{delay}s'><div class='map-tl-icon'>{icon}</div><div class='map-tl-content'><div class='tl-time' style='color:#8E2F2F; font-weight:bold;'>{item['time']}</div><div style='font-weight:900; font-size:1.1rem;'>{item['title']}</div><div style='font-size:0.85rem; color:#666;'>{loc_text}</div></div></div>")
            
        t_html.append('</div>')
        st.markdown("".join(t_html), unsafe_allow_html=True)
    else:
        st.info("🌸 本日尚無行程，請去規劃頁面添加！")

# ==========================================
# 3. 準備清單 (回歸！打勾功能)
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
        st.error("資料格式錯誤，請刷新頁面。")
        st.session_state.checklist = default_checklist
        st.rerun()

    st.markdown("### 🇯🇵 旅日注意事項")
    with st.container(border=True):
        tips_html = """
        <ul>
        <li><b>🔌 電壓</b>：日本電壓 100V，插座為雙平腳（與台灣相同）。</li>
        <li><b>💰 退稅</b>：同日同店消費滿 <b>5,000日圓</b> (未稅) 可退稅 10%。</li>
        <li><b>🚆 交通</b>：建議使用 <b>Suica / ICOCA</b> 綁定 Apple Pay。</li>
        <li><b>🗑️ 垃圾</b>：街道垃圾桶極少，請自行帶回飯店。</li>
        </ul>
        """
        st.markdown(tips_html, unsafe_allow_html=True)