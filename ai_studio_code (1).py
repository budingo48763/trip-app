import streamlit as st

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="長野・名古屋之旅", page_icon="🗾", layout="centered")

# -------------------------------------
# 2. 自定義 CSS
# -------------------------------------
st.markdown("""
    <style>
    .stApp { font-family: 'Helvetica Neue', Helvetica, 'Microsoft JhengHei', Arial, sans-serif; background-color: #F8F9FA; }
    .stDeployButton, header {visibility: hidden;}

    /* 頂部資訊卡 */
    .header-card {
        background: white; padding: 20px 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px;
    }
    .header-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .header-time { font-size: 3rem; font-weight: 800; color: #333; line-height: 1; }
    .header-day { font-size: 1.1rem; color: #999; margin-left: 10px; margin-top: 15px;}
    .header-route { font-size: 1.3rem; font-weight: 700; color: #444; margin-top: 10px; }
    
    /* 天氣 */
    .weather-box { text-align: right; }
    .weather-temp { font-size: 1.6rem; font-weight: 800; color: #333; }
    .weather-desc { font-size: 0.85rem; color: #888; background: #eee; padding: 2px 8px; border-radius: 6px; }

    /* Day 按鈕樣式 */
    div[role="radiogroup"] { gap: 8px; overflow-x: auto; padding-bottom: 5px; }
    div[role="radiogroup"] label > div:first-child { display: none; }
    div[role="radiogroup"] label {
        background: white !important; border: 1px solid #ddd; padding: 6px 14px !important;
        border-radius: 10px !important; transition: all 0.2s;
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background: #333 !important; color: white !important; border-color: #333;
    }

    /* 時間軸線條 */
    .timeline-wrapper { position: relative; padding-left: 10px; }
    .timeline-line {
        position: absolute; left: 69px; top: 0; bottom: 0; width: 2px; background: #E0E0E0; z-index: 0;
    }
    
    /* 卡片樣式 */
    .trip-card {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #ccc;
        margin-bottom: 15px;
        width: 100%;
        position: relative;
        z-index: 1;
    }
    .card-content-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
    .card-title { font-size: 1.1rem; font-weight: 700; color: #222; margin: 0; }
    .card-price { background: #F3F4F6; color: #555; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 600; white-space: nowrap; }
    .card-loc a { color: #666; text-decoration: none; font-size: 0.9rem; display: flex; align-items: center; gap: 5px; }
    .card-note { font-size: 0.85rem; color: #999; margin-top: 4px; font-style: italic; }

    /* 時間與圓點 */
    .time-col { font-size: 1.1rem; font-weight: 700; color: #444; text-align: right; padding-right: 10px; }
    .dot-col { display: flex; justify-content: center; }
    .timeline-dot {
        width: 12px; height: 12px; background: white;
        border: 3px solid #FF5A5F; border-radius: 50%;
        margin-top: 5px; position: relative; z-index: 2;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 資料初始化
# -------------------------------------
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id": 101, "time": "11:35", "title": "抵達名古屋", "loc": "中部國際機場", "cost": 0, "cat": "trans", "note": ""}],
        2: [
            {"id": 201, "time": "07:00", "title": "起床 & 早餐", "loc": "相鐵FRESA INN", "cost": 0, "cat": "stay", "note": "晨跑"},
            {"id": 202, "time": "08:00", "title": "移動：名古屋 → 上諏訪", "loc": "JR 特急 (信濃號)", "cost": 0, "cat": "trans", "note": "指定席"},
            {"id": 203, "time": "10:30", "title": "放行李", "loc": "ホテル紅や", "cost": 0, "cat": "stay", "note": "寄放行李"},
            {"id": 204, "time": "11:30", "title": "午餐：鰻魚飯", "loc": "ねばし (古名店)", "cost": 2000, "cat": "food", "note": "排隊美食"},
            {"id": 205, "time": "13:30", "title": "高島城跡", "loc": "高島城", "cost": 0, "cat": "play", "note": "散步拍照"},
            {"id": 206, "time": "18:00", "title": "晚餐", "loc": "Izumiya", "cost": 1500, "cat": "food", "note": ""},
        ],
        3: [], 4: [], 5: [], 6: [], 7: []
    }

# -------------------------------------
# 4. 主畫面渲染
# -------------------------------------
days_map = {1: "週日", 2: "週一", 3: "週二", 4: "週三", 5: "週四", 6: "週五", 7: "週六"}

# Day 選擇器
selected_day = st.radio(
    "選擇天數", [1, 2, 3, 4, 5, 6, 7], 
    index=1, 
    format_func=lambda x: f"Day {x}", 
    horizontal=True,
    label_visibility="collapsed"
)

current_items = st.session_state.trip_data[selected_day]
total_cost = sum(i['cost'] for i in current_items)
day_str = days_map.get(selected_day, "")

# Header HTML (這裡也去掉縮排)
header_html = f"""<div class="header-card"><div class="header-top"><div style="display:flex;"><div class="header-time">11:35</div><div class="header-day">{day_str}</div></div><div class="weather-box"><div class="weather-temp">12°</div><div class="weather-desc">舒適涼爽</div></div></div><div class="header-route">名古屋 ✈️ 上諏訪</div></div>"""
st.markdown(header_html, unsafe_allow_html=True)

# 工具列
col_info, col_edit = st.columns([3, 1])
col_info.caption(f"Day {selected_day} 行程 • 預算 ¥{total_cost:,}")
is_edit = col_edit.checkbox("編輯模式", value=False)

cat_colors = {"food": "#FF6B6B", "trans": "#4ECDC4", "stay": "#5E548E", "play": "#FFD93D", "other": "#95A5A6"}

st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)

if not current_items:
    st.info("😴 今天沒有行程")

for item in current_items:
    c1, c2, c3 = st.columns([1, 0.4, 5])
    
    with c1:
        st.markdown(f'<div class="time-col">{item["time"]}</div>', unsafe_allow_html=True)
    
    with c2:
        color = cat_colors.get(item.get("cat", "other"), "#999")
        st.markdown(f'<div class="dot-col"><div class="timeline-dot" style="border-color:{color}"></div></div>', unsafe_allow_html=True)
    
    with c3:
        if is_edit:
            with st.expander(f"📝 {item['title']}", expanded=True):
                new_title = st.text_input("標題", item['title'], key=f"t_{item['id']}")
                c_a, c_b = st.columns(2)
                item['time'] = c_a.text_input("時間", item['time'], key=f"tm_{item['id']}")
                item['cost'] = c_b.number_input("金額", value=item['cost'], step=100, key=f"c_{item['id']}")
                item['loc'] = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                item['title'] = new_title
        else:
            # -------------------------------------------------------------
            # ⚠️ 關鍵修正：將 HTML 壓縮成一行，不要有換行符號
            # -------------------------------------------------------------
            border_color = cat_colors.get(item.get("cat", "other"), "#ccc")
            price_html = f'<div class="card-price">¥{item["cost"]:,}</div>' if item["cost"] > 0 else ""
            loc_link = f'https://www.google.com/maps/search/?api=1&query={item["loc"]}'
            loc_html = f'<div class="card-loc"><a href="{loc_link}" target="_blank">📍 {item["loc"]}</a></div>' if item['loc'] else ""
            note_html = f'<div class="card-note">{item["note"]}</div>' if item["note"] else ""
            
            # 這裡把所有字串接起來，不使用多行字串 (f"""...""")，解決 HTML 外洩問題
            full_html = (
                f'<div class="trip-card" style="border-left-color: {border_color};">'
                f'<div class="card-content-row"><div class="card-title">{item["title"]}</div>{price_html}</div>'
                f'{loc_html}{note_html}</div>'
            )
            
            st.markdown(full_html, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
