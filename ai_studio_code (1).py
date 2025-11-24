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
# 2. 日式復古風 CSS (大正浪漫風格)
# -------------------------------------
st.markdown("""
    <style>
    /* 全局設定：米色背景、襯線字體、墨色文字 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important; /* 米色紙張感 */
        color: #2B2B2B !important; /* 墨色 */
        font-family: 'Noto Serif JP', 'Hiragino Mincho ProN', 'Yu Mincho', serif !important;
    }
    
    /* 隱藏原生多餘元素 */
    .stDeployButton, header {visibility: hidden;}

    /* ----------------------------------
       輸入元件優化 (復古風格)
       ---------------------------------- */
    /* 輸入框：透明底、下底線風格 (類似填寫紙本) */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 2px solid #8E2F2F !important; /* 朱紅底線 */
        border-radius: 0 !important;
    }
    input, textarea {
        color: #2B2B2B !important;
        font-family: 'Noto Serif JP', serif !important;
        font-weight: bold !important;
        background-color: transparent !important;
    }
    /* 時間選擇器優化 */
    div[data-baseweb="timepicker"] {
        background-color: #FFF !important;
    }
    
    /* ----------------------------------
       Day 選擇器 (模仿圖片中的方框設計)
       ---------------------------------- */
    div[role="radiogroup"] { gap: 12px; padding: 10px 0; justify-content: center; display: flex;}
    div[role="radiogroup"] label > div:first-child { display: none; } 

    /* 未選中：白底、細框、灰色字 */
    div[role="radiogroup"] label {
        background-color: #FFFFFF !important;
        border: 1px solid #D0C9C0 !important;
        width: 50px !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 2px !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    div[role="radiogroup"] label p {
        color: #999 !important;
        font-family: 'Noto Serif JP', serif !important;
        font-size: 1.1rem !important;
        line-height: 1.2 !important;
        text-align: center !important;
    }

    /* 選中：朱紅底、白字 */
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #8E2F2F !important; /* 朱紅色 */
        border-color: #8E2F2F !important;
    }
    div[role="radiogroup"] label[data-checked="true"] p {
        color: #FFFFFF !important;
    }

    /* ----------------------------------
       UI 卡片設計
       ---------------------------------- */
    /* 頂部大標題 */
    .retro-title {
        font-size: 3.5rem; color: #8E2F2F; text-align: center; font-weight: 900; margin-bottom: 0px; letter-spacing: 2px;
    }
    .retro-subtitle {
        font-size: 1.2rem; color: #555; text-align: center; margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px;
    }

    /* 行程卡片：左側紅線風格 */
    .timeline-wrapper { position: relative; padding-left: 20px; margin-top: 20px;}
    .timeline-line {
        position: absolute; left: 88px; top: 0; bottom: 0; width: 1px; border-left: 2px dotted #8E2F2F; z-index: 0;
    }
    
    .trip-card {
        background: #FFFFFF; 
        border: 1px solid #EBE6DE;
        border-left: 6px solid #8E2F2F; /* 朱紅飾條 */
        padding: 15px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(142, 47, 47, 0.05);
        position: relative; z-index: 1;
    }
    .card-time { font-family: 'Noto Serif JP', serif; font-size: 1.8rem; font-weight: 700; color: #2B2B2B; line-height: 1;}
    .card-title { font-size: 1.3rem; font-weight: 900; color: #2B2B2B; margin-bottom: 5px; }
    .card-loc { color: #8E2F2F; font-size: 0.95rem; font-weight: 600; display: flex; align-items: center; gap: 5px; }
    .card-loc a { color: #8E2F2F; text-decoration: none; border-bottom: 1px solid #8E2F2F; }
    .card-note { color: #666; font-size: 0.9rem; margin-top: 8px; font-style: italic; background: #F7F7F7; padding: 5px 10px; border-radius: 4px;}
    .card-price { float: right; background: #8E2F2F; color: white; padding: 2px 8px; font-size: 0.8rem; border-radius: 2px;}

    /* 天氣標籤 */
    .weather-tag {
        position: absolute; top: 15px; right: 15px;
        text-align: right;
    }
    .w-temp { font-size: 1.2rem; font-weight: bold; color: #555; }
    .w-desc { font-size: 0.8rem; color: #888; }
    
    /* 編輯區塊 */
    .streamlit-expanderHeader { background: #FAF9F6 !important; border: 1px solid #ddd !important; color: #333 !important; }
    .streamlit-expanderContent { background: #fff !important; border: 1px solid #ddd !important; border-top: none !important;}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 輔助函數 (天氣、地圖)
# -------------------------------------
def get_mock_weather(location):
    """ 模擬天氣 (根據地點隨機回傳，實作可接 API) """
    if not location: return "", ""
    weathers = ["☀️ 晴", "⛅ 多雲", "☁️ 陰", "🌧️ 小雨"]
    temps = range(8, 20)
    # 用地點名稱當種子，讓同一地點每次顯示天氣一樣
    random.seed(len(location)) 
    return random.choice(weathers), f"{random.choice(temps)}°C"

def generate_google_map_route(items):
    """ 產生 Google Maps 路線連結 """
    if len(items) < 1: return "#"
    base_url = "https://www.google.com/maps/dir/"
    locations = [urllib.parse.quote(item['loc']) for item in items if item['loc']]
    if not locations: return "#"
    return base_url + "/".join(locations)

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
        "護照": False, "日幣現金": False, "信用卡": False, "eSIM/網卡": False,
        "行動電源": False, "充電器": False, "常備藥品": False, "換洗衣物": False
    }

# -------------------------------------
# 5. 側邊欄導航
# -------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ 設定")
    start_date = st.date_input("出發日期", value=datetime.today())
    trip_days_count = st.number_input("旅遊天數", 1, 30, 5)
    
    st.markdown("---")
    st.markdown("### 🏮 導航")
    page = st.radio("選擇頁面", ["📅 行程規劃", "🗺️ 路線全覽", "🎒 準備清單"], label_visibility="collapsed")
    
    st.markdown("---")
    is_edit_mode = st.toggle("✏️ 編輯模式", value=False)

# 初始化天數資料
for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

# ==========================================
# 頁面 1: 行程規劃 (主頁面)
# ==========================================
if page == "📅 行程規劃":
    # 標題區
    st.markdown('<div class="retro-title">長野・名古屋</div>', unsafe_allow_html=True)
    st.markdown('<div class="retro-subtitle">NAGANO & NAGOYA CLASSIC TRIP</div>', unsafe_allow_html=True)

    # Day 選擇器 (模仿圖片方框)
    # 使用 format_func 讓它顯示 Day\n1 的效果 (透過 CSS 控制換行和樣式)
    selected_day_num = st.radio(
        "選擇天數", list(range(1, trip_days_count + 1)), 
        index=0, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: f"Day\n{x}" 
    )

    # 日期計算
    current_date = start_date + timedelta(days=selected_day_num - 1)
    date_str = current_date.strftime("%Y.%m.%d")
    week_str = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][int(current_date.strftime("%w"))]

    # 當日資訊列
    current_items = st.session_state.trip_data[selected_day_num]
    total_cost = sum(i['cost'] for i in current_items)
    
    col_d1, col_d2 = st.columns([2, 1])
    col_d1.markdown(f"## {date_str} <span style='font-size:1rem; color:#8E2F2F;'>{week_str}</span>", unsafe_allow_html=True)
    col_d2.markdown(f"<div style='text-align:right; padding-top:10px;'><b>預算 ¥{total_cost:,}</b></div>", unsafe_allow_html=True)

    # 新增按鈕
    if is_edit_mode:
        if st.button("➕ 新增行程", type="primary", use_container_width=True):
            st.session_state.trip_data[selected_day_num].append({
                "id": int(datetime.now().timestamp()), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": ""
            })
            st.rerun()

    # 行程列表
    st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)
    
    current_items.sort(key=lambda x: x['time'])
    
    if not current_items:
        st.info("🍵 本日尚無行程，請點擊編輯模式新增。")

    for index, item in enumerate(current_items):
        # 1. 時間欄位 (左側)
        c_time, c_content = st.columns([1.2, 4])
        
        with c_time:
            st.markdown(f"<div class='card-time' style='text-align:right; padding-top:20px;'>{item['time']}</div>", unsafe_allow_html=True)
            # 裝飾用圓點
            st.markdown("<div style='float:right; margin-right:-26px; margin-top:-30px; width:12px; height:12px; background:#8E2F2F; border-radius:50%; position:relative; z-index:2; border:2px solid #FDFCF5;'></div>", unsafe_allow_html=True)

        with c_content:
            if is_edit_mode:
                # --- 編輯模式 ---
                with st.expander(f"📝 {item['title']}", expanded=True):
                    # 標題與刪除
                    c_t, c_del = st.columns([5, 1])
                    new_title = c_t.text_input("行程標題", item['title'], key=f"t_{item['id']}")
                    if c_del.button("🗑️", key=f"d_{item['id']}"):
                        st.session_state.trip_data[selected_day_num].pop(index)
                        st.rerun()
                    
                    # 時間與金額 (使用 st.time_input 滿足需求)
                    c1, c2 = st.columns(2)
                    # 將字串轉為 datetime.time 物件給 time_input 使用
                    try:
                        t_obj = datetime.strptime(item['time'], "%H:%M").time()
                    except:
                        t_obj = datetime.strptime("00:00", "%H:%M").time()
                        
                    new_time_obj = c1.time_input("時間", value=t_obj, key=f"tm_{item['id']}")
                    item['time'] = new_time_obj.strftime("%H:%M") # 存回字串
                    
                    item['cost'] = c2.number_input("金額 (JPY)", value=item['cost'], step=100, key=f"c_{item['id']}")
                    item['loc'] = st.text_input("地點 (用於天氣與地圖)", item['loc'], key=f"l_{item['id']}")
                    item['note'] = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                    item['title'] = new_title
            else:
                # --- 瀏覽模式 (復古卡片) ---
                w_icon, w_temp = get_mock_weather(item['loc'])
                weather_html = f"<div class='weather-tag'><div class='w-temp'>{w_icon} {w_temp}</div></div>" if item['loc'] else ""
                
                # 金額標籤
                price_tag = f"<span class='card-price'>¥{item['cost']:,}</span>" if item['cost'] > 0 else ""
                
                # 地點連結
                loc_html = ""
                if item['loc']:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={item['loc']}"
                    loc_html = f"<div class='card-loc'>📍 <a href='{map_url}' target='_blank'>{item['loc']}</a></div>"
                
                # 備註
                note_html = f"<div class='card-note'>{item['note']}</div>" if item['note'] else ""

                card_html = f"""
                <div class="trip-card">
                    {weather_html}
                    <div class="card-title">{item['title']} {price_tag}</div>
                    {loc_html}
                    {note_html}
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
    st.markdown('</div>', unsafe_allow_html=True)

    # 底部：產生當日 Google Maps 路線按鈕
    if current_items:
        st.markdown("---")
        route_url = generate_google_map_route(current_items)
        st.markdown(f"""
        <div style="text-align:center;">
            <a href="{route_url}" target="_blank" style="background:#8E2F2F; color:white; padding:10px 20px; border-radius:30px; text-decoration:none; font-weight:bold;">
                🚗 開啟 Google Maps 路線導航
            </a>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 頁面 2: 路線全覽 (Graphviz 串聯)
# ==========================================
elif page == "🗺️ 路線全覽":
    st.markdown('<div class="retro-title">路線地圖</div>', unsafe_allow_html=True)
    st.info("此圖表自動將您的行程依時間順序串聯。")

    day_opts = list(range(1, trip_days_count + 1))
    map_day = st.selectbox("選擇要查看的天數", day_opts, format_func=lambda x: f"Day {x}")
    
    map_items = st.session_state.trip_data[map_day]
    map_items.sort(key=lambda x: x['time'])
    
    if len(map_items) > 1:
        # 使用 Graphviz 畫出漂亮的流程圖
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR') # 左到右排列
        dot.attr('node', shape='box', style='filled', fillcolor='#FDFCF5', color='#8E2F2F', fontname='Noto Serif JP')
        
        last_node = None
        for item in map_items:
            # 節點標籤：時間 + 地點/標題
            label = f"{item['time']}\n{item['loc'] or item['title']}"
            node_id = str(item['id'])
            dot.node(node_id, label)
            
            if last_node:
                dot.edge(last_node, node_id, color="#8E2F2F", penwidth="2")
            last_node = node_id
            
        st.graphviz_chart(dot)
    else:
        st.warning("行程過少，無法繪製路線圖，請至少新增兩個行程。")

# ==========================================
# 頁面 3: 準備清單 (新增功能)
# ==========================================
elif page == "🎒 準備清單":
    st.markdown('<div class="retro-title">旅の支度</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 📋 必備物品")
        # 遍歷並顯示 Checkbox
        keys = list(st.session_state.checklist.keys())
        for k in keys[:4]: # 左欄
            st.session_state.checklist[k] = st.checkbox(k, value=st.session_state.checklist[k])
            
    with c2:
        st.markdown("### 🧳 行李衣物")
        for k in keys[4:]: # 右欄
            st.session_state.checklist[k] = st.checkbox(k, value=st.session_state.checklist[k])

    st.markdown("### ⚠️ 注意事項")
    st.warning("""
    1. **電壓**: 日本電壓為 100V，插座為雙平腳（A型），台灣電器通常可直接使用。
    2. **退稅**: 購物滿 5,000 日圓（未稅）可辦理退稅，請隨身攜帶護照。
    3. **交通**: 建議綁定西瓜卡 (Suica) 或 ICOCA 至手機，進出站更方便。
    """)
    
    st.text_area("📝 個人備忘錄", placeholder="在此輸入其他需要攜帶的物品...")
