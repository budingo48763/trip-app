import streamlit as st
from datetime import datetime, timedelta
import random
import graphviz
import urllib.parse

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="旅日計畫書", page_icon="⛩️", layout="centered")

# -------------------------------------
# 2. 日式復古風 CSS (完美還原 Day 按鈕版)
# -------------------------------------
st.markdown("""
    <style>
    /* 全局字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important; /* 米色紙張感 */
        color: #2B2B2B !important; 
        font-family: 'Noto Serif JP', 'Times New Roman', serif !important;
    }
    
    .stDeployButton, header {visibility: hidden;}

    /* =========================================
       1. 側邊欄導航 (保持長條清單)
       ========================================= */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex; flex-direction: column; gap: 8px;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        width: 100% !important;
        height: auto !important;
        padding: 10px 15px !important;
        border: none !important;
        border-bottom: 1px solid #ddd !important;
        background: transparent !important;
        justify-content: flex-start !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 1.1rem !important;
        color: #555 !important;
        font-weight: bold !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background-color: rgba(142, 47, 47, 0.1) !important;
        border-left: 5px solid #8E2F2F !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p {
        color: #8E2F2F !important;
    }

    /* =========================================
       2. 主畫面 Day 按鈕 (圖片風格完美還原)
       ========================================= */
    /* 容器設定 */
    .stMain div[role="radiogroup"] { 
        gap: 12px; padding: 10px 0; justify-content: center; display: flex; flex-wrap: wrap;
    }
    /* 隱藏預設圓點 */
    .stMain div[role="radiogroup"] label > div:first-child { display: none; }
    
    /* 按鈕本體 (未選中) */
    .stMain div[role="radiogroup"] label {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important; /* 極細灰框 */
        width: 55px !important;
        height: 75px !important; /* 拉長比例 */
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 0px !important; /* 直角風格 */
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* 文字共用設定 */
    .stMain div[role="radiogroup"] label p {
        font-family: 'Times New Roman', 'Noto Serif JP', serif !important;
        text-align: center !important;
        white-space: pre-wrap !important; /* 允許換行 */
        line-height: 1.2 !important;
        width: 100% !important;
        margin: 0 !important;
        display: block !important;
    }

    /* --- 針對數字 (預設樣式) --- */
    .stMain div[role="radiogroup"] label p {
        font-size: 2rem !important; /* 數字超大 */
        font-weight: 500 !important;
        color: #666 !important; /* 未選中數字顏色 */
    }

    /* --- 針對 "Day" (利用第一行偽元素) --- */
    .stMain div[role="radiogroup"] label p::first-line {
        font-size: 0.8rem !important; /* Day 字體小 */
        color: #AAA !important; /* Day 顏色淡 */
        font-weight: 400 !important;
        line-height: 2 !important; /* 增加 Day 與數字的間距 */
    }

    /* --- 選中狀態 (深紅背景) --- */
    .stMain div[role="radiogroup"] label[data-checked="true"] {
        background-color: #8E2F2F !important;
        border: 1px solid #8E2F2F !important;
        box-shadow: 0 4px 10px rgba(142, 47, 47, 0.2) !important;
    }

    /* 選中時的文字顏色 */
    .stMain div[role="radiogroup"] label[data-checked="true"] p {
        color: #FFFFFF !important; /* 數字變白 */
    }
    .stMain div[role="radiogroup"] label[data-checked="true"] p::first-line {
        color: rgba(255, 255, 255, 0.7) !important; /* Day 變微透明白 */
    }

    /* =========================================
       3. 其他 UI 優化
       ========================================= */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid #8E2F2F !important;
        border-radius: 0 !important;
    }
    input, textarea { color: #2B2B2B !important; font-weight: bold !important; background-color: transparent !important; }
    div[data-baseweb="timepicker"] { background-color: #FFF !important; }

    /* 卡片設計 */
    .trip-card {
        background: #FFFFFF; 
        border: 1px solid #EBE6DE;
        border-left: 6px solid #8E2F2F;
        padding: 15px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(142, 47, 47, 0.05);
        position: relative; 
    }
    .card-header { display: flex; justify-content: space-between; align-items: flex-start; padding-right: 70px; margin-bottom: 10px; }
    .card-title-group { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .card-title { font-size: 1.3rem; font-weight: 900; color: #2B2B2B; margin: 0; }
    .card-price { background: #8E2F2F; color: white; padding: 3px 8px; font-size: 0.85rem; border-radius: 4px; font-weight: bold; white-space: nowrap; }
    .weather-tag { position: absolute; top: 15px; right: 15px; text-align: right; background: #FDFCF5; padding: 2px 5px; border-radius: 4px; }
    .w-temp { font-size: 1.1rem; font-weight: bold; color: #555; }
    .card-time { font-family: 'Noto Serif JP', serif; font-size: 1.8rem; font-weight: 700; color: #2B2B2B; text-align: right; margin-top: 10px;}
    .card-loc a { color: #8E2F2F; text-decoration: none; border-bottom: 1px solid #8E2F2F; font-weight: bold;}
    .card-note { color: #666; font-size: 0.9rem; margin-top: 8px; font-style: italic; background: #F7F7F7; padding: 5px 10px; border-radius: 4px;}
    .timeline-line { position: absolute; left: 88px; top: 0; bottom: 0; width: 1px; border-left: 2px dotted #8E2F2F; z-index: 0; }
    .retro-title { font-size: 3rem; color: #8E2F2F; text-align: center; font-weight: 900; letter-spacing: 2px; }
    .retro-subtitle { font-size: 1rem; color: #888; text-align: center; margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 輔助函數
# -------------------------------------
def get_mock_weather(location):
    if not location: return "", ""
    weathers = ["☀️ 晴", "⛅ 多雲", "🌧️ 雨", "❄️ 雪"]
    random.seed(len(location) + datetime.now().day) 
    return random.choice(weathers), f"{random.randint(5, 18)}°C"

def generate_google_map_route(items):
    if len(items) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    locations = [urllib.parse.quote(item['loc']) for item in items if item['loc']]
    return base_url + "/".join(locations) if locations else "#"

# -------------------------------------
# 4. 資料初始化
# -------------------------------------
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id": 101, "time": "11:35", "title": "抵達名古屋", "loc": "中部國際機場", "cost": 0, "cat": "trans", "note": ""}],
        2: [
            {"id": 201, "time": "07:00", "title": "起床 & 早餐", "loc": "相鐵FRESA INN", "cost": 0, "cat": "stay", "note": "晨跑"},
            {"id": 202, "time": "08:00", "title": "移動：名古屋 → 上諏訪", "loc": "JR 特急 (信濃號)", "cost": 0, "cat": "trans", "note": "指定席"},
            {"id": 203, "time": "10:30", "title": "放行李", "loc": "ホテル紅や", "cost": 0, "cat": "stay", "note": "寄放行李"},
            {"id": 204, "time": "11:30", "title": "午餐：鰻魚飯", "loc": "ねばし (古名店)", "cost": 2000, "cat": "food", "note": "排隊美食"},
        ]
    }
if "checklist" not in st.session_state:
    st.session_state.checklist = {
        "護照": False, "日幣": False, "信用卡": False, "網卡": False,
        "充電器": False, "常備藥": False, "換洗衣物": False, "盥洗具": False
    }

# -------------------------------------
# 5. 側邊欄導航
# -------------------------------------
with st.sidebar:
    st.title("🏮 旅日手帖")
    page = st.radio("導航", ["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單"], label_visibility="collapsed")
    st.divider()
    st.markdown("### ⚙️ 設定")
    start_date = st.date_input("出發日期", value=datetime.today())
    trip_days_count = st.number_input("旅遊天數", 1, 30, 5)
    is_edit_mode = st.toggle("✏️ 編輯模式", value=False)

for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

# ==========================================
# 頁面 1: 行程規劃
# ==========================================
if page == "📅 行程規劃":
    st.markdown('<div class="retro-title">長野・名古屋</div>', unsafe_allow_html=True)
    st.markdown('<div class="retro-subtitle">CLASSIC TRIP PLANNER</div>', unsafe_allow_html=True)

    # ⚠️ 這裡保持不變，樣式交給上面的 CSS ::first-line 處理
    selected_day_num = st.radio(
        "DaySelect", list(range(1, trip_days_count + 1)), 
        index=0, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: f"Day\n{x}" 
    )

    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]

    current_items = st.session_state.trip_data[selected_day_num]
    total_cost = sum(i['cost'] for i in current_items)
    
    c_info1, c_info2 = st.columns([2, 1])
    c_info1.markdown(f"### 🗓️ {date_str} {week_str}")
    c_info2.markdown(f"<div style='text-align:right; color:#8E2F2F; font-weight:bold; padding-top:10px;'>本日預算 ¥{total_cost:,}</div>", unsafe_allow_html=True)

    if is_edit_mode:
        if st.button("➕ 新增行程", type="primary", use_container_width=True):
            st.session_state.trip_data[selected_day_num].append({
                "id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": ""
            })
            st.rerun()

    st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)
    
    current_items.sort(key=lambda x: x['time'])
    
    if not current_items:
        st.info("🍵 請點擊編輯模式開始規劃行程。")

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
                    new_title = c_title_input.text_input("標題", item['title'], key=f"t_{item['id']}", label_visibility="collapsed")
                    item['title'] = new_title

                    c1, c2 = st.columns(2)
                    try: t_obj = datetime.strptime(item['time'], "%H:%M").time()
                    except: t_obj = datetime.strptime("09:00", "%H:%M").time()
                    item['time'] = c1.time_input("時間", value=t_obj, key=f"tm_{item['id']}").strftime("%H:%M")
                    item['cost'] = c2.number_input("金額", value=item['cost'], step=100, key=f"c_{item['id']}")
                    item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                    item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
            else:
                w_icon, w_temp = get_mock_weather(item['loc'])
                weather_html = f"<div class='weather-tag'><div class='w-temp'>{w_icon} {w_temp}</div></div>" if item['loc'] else ""
                price_html = f"<div class='card-price'>¥{item['cost']:,}</div>" if item['cost'] > 0 else ""
                loc_html = ""
                if item['loc']:
                    url = f"https://www.google.com/maps/search/?api=1&query={item['loc']}"
                    loc_html = f"<div class='card-loc'>📍 <a href='{url}' target='_blank'>{item['loc']}</a></div>"
                note_html = f"<div class='card-note'>{item['note']}</div>" if item['note'] else ""

                card_html = (
                    f'<div class="trip-card">'
                    f'{weather_html}'
                    f'<div class="card-header">'
                    f'<div class="card-title-group"><div class="card-title">{item["title"]}</div>{price_html}</div>'
                    f'</div>'
                    f'{loc_html}'
                    f'{note_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)

    if current_items:
        st.markdown("---")
        route_url = generate_google_map_route(current_items)
        st.markdown(f"<div style='text-align:center;'><a href='{route_url}' target='_blank' style='background:#8E2F2F; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 Google Maps 路線導航</a></div>", unsafe_allow_html=True)

elif page == "🗺️ 路線全覽":
    st.markdown('<div class="retro-title">路線地圖</div>', unsafe_allow_html=True)
    map_day = st.selectbox("選擇天數", list(range(1, trip_days_count + 1)), format_func=lambda x: f"Day {x}")
    map_items = st.session_state.trip_data[map_day]
    map_items.sort(key=lambda x: x['time'])
    
    if len(map_items) > 1:
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR')
        dot.attr('node', shape='note', style='filled', fillcolor='#FDFCF5', color='#8E2F2F', fontname='Noto Serif JP')
        last = None
        for item in map_items:
            label = f"{item['time']}\n{item['loc'] or item['title']}"
            dot.node(str(item['id']), label)
            if last: dot.edge(last, str(item['id']), color="#8E2F2F")
            last = str(item['id'])
        st.graphviz_chart(dot)
    else:
        st.info("行程過少，無法繪製路線。")

elif page == "🎒 準備清單":
    st.markdown('<div class="retro-title">旅の支度</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    keys = list(st.session_state.checklist.keys())
    with c1:
        st.markdown("##### 🛂 必要證件")
        for k in keys[:4]: st.session_state.checklist[k] = st.checkbox(k, value=st.session_state.checklist[k])
    with c2:
        st.markdown("##### 🧳 生活用品")
        for k in keys[4:]: st.session_state.checklist[k] = st.checkbox(k, value=st.session_state.checklist[k])
