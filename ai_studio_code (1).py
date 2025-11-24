import streamlit as st
from datetime import datetime, timedelta
import random
import graphviz
import urllib.parse  # 確保這行有被匯入

# -------------------------------------
# 1. 系統設定 (必須是第一行)
# -------------------------------------
st.set_page_config(page_title="旅日計畫書", page_icon="⛩️", layout="centered", initial_sidebar_state="collapsed")

# -------------------------------------
# 2. 輔助函數定義 (必須放在主程式之前)
# -------------------------------------

# (A) 新增消費明細的回調函數
def add_expense_callback(item, name_key, price_key):
    new_name = st.session_state.get(name_key, "")
    new_price = st.session_state.get(price_key, 0)
    if new_name:
        item["expenses"].append({"name": new_name, "price": new_price})
        item['cost'] = sum(x['price'] for x in item['expenses'])
        st.session_state[name_key] = ""
        st.session_state[price_key] = 0

# (B) 產生天氣模擬資料
def get_mock_weather(location):
    if not location: return "", ""
    weathers = ["☀️ 晴", "⛅ 多雲", "🌧️ 雨", "❄️ 雪"]
    random.seed(len(location) + datetime.now().day) 
    return random.choice(weathers), f"{random.randint(5, 18)}°C"

# (C) 產生 Google Maps 路線連結 (這就是剛剛報錯遺失的函數)
def generate_google_map_route(items):
    if len(items) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    # 這裡使用 urllib.parse 來處理網址編碼
    locations = [urllib.parse.quote(item['loc']) for item in items if item['loc']]
    return base_url + "/".join(locations) if locations else "#"

# -------------------------------------
# 3. 日式復古風 CSS & 介面優化
# -------------------------------------
st.markdown("""
    <style>
    /* 全局字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important;
        color: #2B2B2B !important; 
        font-family: 'Noto Serif JP', 'Times New Roman', serif !important;
    }

    /* =========================================================
       🛑 隱藏側邊欄與多餘介面
       ========================================================= */
    [data-testid="stSidebarCollapsedControl"], section[data-testid="stSidebar"] {
        display: none !important;
    }
    div[data-testid="stToolbar"], div[data-testid="stDecoration"], footer {
        visibility: hidden !important;
        display: none !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 0 !important;
    }

    /* =========================================================
       📑 分頁 (Tabs) 樣式
       ========================================================= */
    button[data-baseweb="tab"] {
        font-family: 'Noto Serif JP', serif !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #888 !important;
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #8E2F2F !important;
        border-bottom: 3px solid #8E2F2F !important;
    }
    div[data-baseweb="tab-highlight"] { display: none !important; }
    div[data-baseweb="tab-list"] { gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #ddd; }

    /* =========================================================
       其他 UI 元件
       ========================================================= */
    .stMain div[role="radiogroup"] { 
        gap: 8px; padding: 10px 0; justify-content: flex-start; display: flex; overflow-x: auto; 
    }
    .stMain div[role="radiogroup"] label > div:first-child { display: none; }
    .stMain div[role="radiogroup"] label {
        background-color: #FFFFFF !important; border: 1px solid #E0E0E0 !important;
        min-width: 50px !important; height: 70px !important;
        display: flex !important; flex-direction: column !important;
        align-items: center !important; justify-content: center !important;
        border-radius: 0px !important; box-shadow: none !important;
        padding: 0 !important; margin: 0 !important;
    }
    .stMain div[role="radiogroup"] label p {
        font-size: 1.8rem !important; font-weight: 500 !important; color: #666 !important;
        line-height: 1.2 !important; width: 100% !important; margin: 0 !important; text-align: center !important;
    }
    .stMain div[role="radiogroup"] label[data-checked="true"] {
        background-color: #8E2F2F !important; border: 1px solid #8E2F2F !important;
        box-shadow: 0 4px 8px rgba(142, 47, 47, 0.2) !important;
    }
    .stMain div[role="radiogroup"] label[data-checked="true"] p { color: #FFFFFF !important; }
    
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background-color: transparent !important; border: none !important;
        border-bottom: 2px solid #8E2F2F !important; border-radius: 0 !important;
    }
    input, textarea {
        color: #2B2B2B !important; font-weight: bold !important; background-color: transparent !important;
    }
    div[data-baseweb="timepicker"] { background-color: #FFF !important; }
    div[data-testid="stToggle"] { justify-content: flex-end; padding: 5px; }
    
    /* 卡片設計 */
    .trip-card {
        background: #FFFFFF; border: 1px solid #EBE6DE; border-left: 6px solid #8E2F2F;
        padding: 15px 20px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(142, 47, 47, 0.05);
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
    
    .retro-title { font-size: 2.5rem; color: #8E2F2F; text-align: center; font-weight: 900; letter-spacing: 2px; margin-top: 10px;}
    .retro-subtitle { font-size: 0.9rem; color: #888; text-align: center; margin-bottom: 10px; }
    .timeline-line { position: absolute; left: 88px; top: 0; bottom: 0; width: 1px; border-left: 2px dotted #8E2F2F; z-index: 0; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 4. 資料初始化
# -------------------------------------
if "trip_title" not in st.session_state:
    st.session_state.trip_title = "長野・名古屋"

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
if "checklist" not in st.session_state:
    st.session_state.checklist = {
        "護照": False, "日幣": False, "信用卡": False, "網卡": False,
        "充電器": False, "常備藥": False, "換洗衣物": False, "盥洗具": False
    }

# -------------------------------------
# 5. 主畫面 (Tabs 佈局)
# -------------------------------------

# 標題區
st.markdown(f'<div class="retro-title">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown('<div class="retro-subtitle">CLASSIC TRIP PLANNER</div>', unsafe_allow_html=True)

# 設定區 (使用 Expander)
with st.expander("⚙️ 旅程設定 (日期/標題)"):
    st.session_state.trip_title = st.text_input("旅程標題", value=st.session_state.trip_title)
    start_date = st.date_input("出發日期", value=datetime.today())
    trip_days_count = st.number_input("旅遊天數", 1, 30, 5)

# 確保日期資料存在
for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

# 建立分頁
tab1, tab2, tab3 = st.tabs(["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單"])

# ==========================================
# 分頁 1: 行程規劃
# ==========================================
with tab1:
    # Day 選擇器
    selected_day_num = st.radio(
        "DaySelect", list(range(1, trip_days_count + 1)), 
        index=0, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: f"Day\n{x}" 
    )

    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]

    current_items = st.session_state.trip_data[selected_day_num]
    for item in current_items:
        if "expenses" not in item: item["expenses"] = []
    
    total_cost = sum(i['cost'] for i in current_items)
    
    # 標題與編輯開關
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
                # 編輯模式
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
                    
                    c2.markdown(f"**💰 總金額: ¥{item['cost']:,}**")
                    item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                    item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")

                    st.markdown("---")
                    st.caption("🧾 消費明細")
                    
                    if item["expenses"]:
                        for idx, exp in enumerate(item["expenses"]):
                            ce1, ce2, ce3 = st.columns([3, 2, 1])
                            ce1.text(f"• {exp['name']}")
                            ce2.text(f"¥{exp['price']:,}")
                            if ce3.button("✖", key=f"del_exp_{item['id']}_{idx}"):
                                item["expenses"].pop(idx)
                                item['cost'] = sum(x['price'] for x in item['expenses'])
                                st.rerun()

                    c_add1, c_add2, c_add3 = st.columns([3, 2, 1])
                    name_key = f"new_exp_name_{item['id']}"
                    price_key = f"new_exp_price_{item['id']}"

                    with c_add1:
                        st.text_input("項目", key=name_key, placeholder="例: 飲料", label_visibility="collapsed")
                    with c_add2:
                        st.number_input("金額", key=price_key, min_value=0, step=100, label_visibility="collapsed")
                    with c_add3:
                        st.button(
                            "➕", 
                            key=f"btn_add_{item['id']}", 
                            on_click=add_expense_callback, 
                            args=(item, name_key, price_key)
                        )

            else:
                # 瀏覽模式
                w_icon, w_temp = get_mock_weather(item['loc'])
                weather_html = f"<div class='weather-tag'><div class='w-temp'>{w_icon} {w_temp}</div></div>" if item['loc'] else ""
                price_html = f"<div class='card-price'>¥{item['cost']:,}</div>" if item['cost'] > 0 else ""
                loc_html = ""
                if item['loc']:
                    url = f"https://www.google.com/maps/search/?api=1&query={item['loc']}"
                    loc_html = f"<div class='card-loc'>📍 <a href='{url}' target='_blank'>{item['loc']}</a></div>"
                
                note_content = item['note']
                if item['expenses']:
                    exp_list_html = "<div style='margin-top:5px; padding-top:5px; border-top:1px dashed #ccc; font-size:0.85rem;'>"
                    for exp in item['expenses']:
                        exp_list_html += f"<div style='display:flex; justify-content:space-between;'><span>• {exp['name']}</span><span>¥{exp['price']:,}</span></div>"
                    exp_list_html += "</div>"
                    note_content += exp_list_html

                note_html = f"<div class='card-note'>{note_content}</div>" if note_content else ""

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

    # 確保函數存在後再呼叫
    if current_items:
        st.markdown("---")
        try:
            route_url = generate_google_map_route(current_items)
            st.markdown(f"<div style='text-align:center;'><a href='{route_url}' target='_blank' style='background:#8E2F2F; color:white; padding:10px 25px; border-radius:30px; text-decoration:none; font-weight:bold;'>🚗 Google Maps 路線導航</a></div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"地圖產生失敗: {e}")

# ==========================================
# 分頁 2: 路線地圖
# ==========================================
with tab2:
    st.markdown('<div class="retro-subtitle">ROUTE MAP</div>', unsafe_allow_html=True)
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
    else: st.info("行程過少，無法繪製路線。")

# ==========================================
# 分頁 3: 準備清單
# ==========================================
with tab3:
    st.markdown('<div class="retro-subtitle">CHECKLIST</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    keys = list(st.session_state.checklist.keys())
    with c1:
        st.markdown("##### 🛂 必要證件")
        for k in keys[:4]: st.session_state.checklist[k] = st.checkbox(k, value=st.session_state.checklist[k])
    with c2:
        st.markdown("##### 🧳 生活用品")
        for k in keys[4:]: st.session_state.checklist[k] = st.checkbox(k, value=st.session_state.checklist[k])
