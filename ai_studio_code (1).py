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
# 2. 日式復古風 CSS (修復版)
# -------------------------------------
st.markdown("""
    <style>
    /* 全局字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important; /* 米色紙張感 */
        color: #2B2B2B !important; 
        font-family: 'Noto Serif JP', serif !important;
    }
    
    .stDeployButton, header {visibility: hidden;}

    /* =========================================
       1. 導航樣式 (側邊欄與主畫面分離)
       ========================================= */
    
    /* --- 側邊欄 (Sidebar) : 長條清單 --- */
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
        box-shadow: none !important;
        justify-content: flex-start !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 1.1rem !important;
        color: #555 !important;
        font-weight: bold !important;
    }
    /* 側邊欄選中狀態 */
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background-color: rgba(142, 47, 47, 0.1) !important;
        border-left: 5px solid #8E2F2F !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p {
        color: #8E2F2F !important;
    }

    /* --- 主畫面 (Main) : Day 方塊按鈕 --- */
    .stMain div[role="radiogroup"] { 
        gap: 15px; padding: 10px 0; justify-content: center; display: flex; flex-wrap: wrap;
    }
    /* 隱藏圓點 */
    .stMain div[role="radiogroup"] label > div:first-child { display: none; }
    
    /* 未選中方塊 */
    .stMain div[role="radiogroup"] label {
        background-color: #FFFFFF !important;
        border: 1px solid #D0C9C0 !important;
        width: 60px !important;    /* 寬度 */
        height: 80px !important;   /* 高度 (拉長) */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 2px !important;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
        padding: 0 !important;
    }
    /* 文字設定 (關鍵：允許換行) */
    .stMain div[role="radiogroup"] label p {
        color: #aaa !important; /* 淺灰色 Day */
        font-family: 'Noto Serif JP', serif !important;
        font-size: 1.4rem !important; /* 數字大一點 */
        line-height: 1.3 !important;
        text-align: center !important;
        white-space: pre !important; /* ⚠️ 關鍵：讓 Day 和 數字 換行 */
    }

    /* 選中方塊 (深紅底) */
    .stMain div[role="radiogroup"] label[data-checked="true"] {
        background-color: #8E2F2F !important;
        border-color: #8E2F2F !important;
        box-shadow: 0 4px 12px rgba(142, 47, 47, 0.3);
    }
    .stMain div[role="radiogroup"] label[data-checked="true"] p {
        color: #FFFFFF !important;
    }

    /* =========================================
       2. 輸入框與其他 UI
       ========================================= */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid #8E2F2F !important;
        border-radius: 0 !important;
    }
    input, textarea {
        color: #2B2B2B !important;
        font-weight: bold !important;
        background-color: transparent !important;
    }
    div[data-baseweb="timepicker"] { background-color: #FFF !important; }

    /* =========================================
       3. 卡片設計 (HTML 結構安全版)
       ========================================= */
    .trip-card {
        background: #FFFFFF; 
        border: 1px solid #EBE6DE;
        border-left: 6px solid #8E2F2F;
        padding: 15px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(142, 47, 47, 0.05);
        position: relative; 
    }
    
    /* 標題與金額區塊 */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding-right: 70px; /* 避開右上角天氣 */
        margin-bottom: 10px;
    }
    
    .card-title-group { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .card-title { font-size: 1.3rem; font-weight: 900; color: #2B2B2B; margin: 0; }
    
    .card-price { 
        background: #8E2F2F; color: white; 
        padding: 3px 8px; font-size: 0.85rem; 
        border-radius: 4px; font-weight: bold;
        white-space: nowrap;
    }

    /* 天氣 (絕對定位) */
    .weather-tag {
        position: absolute; top: 15px; right: 15px;
        text-align: right;
        background: #FDFCF5; /* 加個背景避免文字干擾 */
        padding: 2px 5px;
        border-radius: 4px;
    }
    .w-temp { font-size: 1.1rem; font-weight: bold; color: #555; }
    
    /* 其他資訊 */
    .card-time { font-family: 'Noto Serif JP', serif; font-size: 1.8rem; font-weight: 700; color: #2B2B2B; text-align: right; margin-top: 10px;}
    .card-loc a { color: #8E2F2F; text-decoration: none; border-bottom: 1px solid #8E2F2F; font-weight: bold;}
    .card-note { color: #666; font-size: 0.9rem; margin-top: 8px; font-style: italic; background: #F7F7F7; padding: 5px 10px; border-radius: 4px;}

    /* 裝飾線 */
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

    # ⚠️ 關鍵：Day 選擇器 (使用 \n 換行)
    selected_day_num = st.radio(
        "DaySelect", list(range(1, trip_days_count + 1)), 
        index=0, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: f"Day\n{x}"  # 這裡的 \n 配合 CSS white-space: pre 達成換行效果
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
                # 編輯模式 (使用 Expander)
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
                # ⚠️ 關鍵修復：HTML 產生 (使用單行字串拼接，杜絕縮排問題)
                w_icon, w_temp = get_mock_weather(item['loc'])
                
                # 1. 天氣 HTML
                weather_html = f"<div class='weather-tag'><div class='w-temp'>{w_icon} {w_temp}</div></div>" if item['loc'] else ""
                
                # 2. 金額 HTML
                price_html = f"<div class='card-price'>¥{item['cost']:,}</div>" if item['cost'] > 0 else ""
                
                # 3. 地點 HTML
                loc_html = ""
                if item['loc']:
                    url = f"https://www.google.com/maps/search/?api=1&query={item['loc']}"
                    loc_html = f"<div class='card-loc'>📍 <a href='{url}' target='_blank'>{item['loc']}</a></div>"
                
                # 4. 備註 HTML
                note_html = f"<div class='card-note'>{item['note']}</div>" if item['note'] else ""

                # 5. 組合所有 HTML (單行)
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

# ==========================================
# 頁面 2 & 3 (路線全覽 / 準備清單)
# ==========================================
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
