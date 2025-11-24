import streamlit as st
from datetime import datetime, timedelta

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="長野・名古屋之旅", page_icon="🗾", layout="centered")

# -------------------------------------
# 2. 自定義 CSS (終極高對比修復版)
# -------------------------------------
st.markdown("""
    <style>
    /* 1. 全局強制亮色背景與黑字 (暴力覆蓋 Streamlit 深色模式設定) */
    .stApp { 
        background-color: #FFFFFF !important; 
        color: #000000 !important;
    }
    
    /* 隱藏原生多餘元素 */
    .stDeployButton, header {visibility: hidden;}

    /* ============================================================
       ⚠️ 關鍵修復：輸入框標籤 (Label) 看不到的問題
       ============================================================ */
    /* 這是「行程標題」、「時間」、「金額」那些字 */
    div[data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 1rem !important;
        visibility: visible !important;
    }
    
    /* 輸入框本體的樣式 (白底、黑字、黑框) */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background-color: #FFFFFF !important;
        border: 2px solid #000000 !important;
        border-radius: 8px !important;
        color: #000000 !important;
    }
    
    /* 輸入框裡面的文字 (使用者打的字) */
    input {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
        font-weight: bold !important;
    }

    /* ============================================================
       ⚠️ 關鍵修復：上方 Day 按鈕看不到字的問題
       ============================================================ */
    /* 按鈕容器 */
    div[role="radiogroup"] { gap: 10px; padding: 10px 0; }
    div[role="radiogroup"] label > div:first-child { display: none; } /* 隱藏原本的圓點 */

    /* 未選中的按鈕：白底、黑字、黑框 */
    div[role="radiogroup"] label {
        background-color: #FFFFFF !important;
        border: 2px solid #000000 !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
    }
    /* 強制未選中按鈕裡面的文字變黑 */
    div[role="radiogroup"] label p {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 1rem !important;
    }

    /* 選中的按鈕：黑底、白字 */
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #000000 !important;
        border-color: #000000 !important;
    }
    /* 強制選中按鈕裡面的文字變白 */
    div[role="radiogroup"] label[data-checked="true"] p {
        color: #FFFFFF !important;
    }

    /* ============================================================
       ⚠️ 關鍵修復：編輯模式的黑色長條 (Expander)
       ============================================================ */
    /* 展開區的標題列 (原本是黑底) 改為淺灰底黑字 */
    .streamlit-expanderHeader {
        background-color: #F0F0F0 !important;
        border: 2px solid #000000 !important;
        border-radius: 8px !important;
        color: #000000 !important;
    }
    /* 展開區標題文字 */
    .streamlit-expanderHeader p {
        color: #000000 !important;
        font-weight: bold !important;
    }
    /* 展開後的內容區塊 */
    .streamlit-expanderContent {
        border-left: 2px solid #000000 !important;
        border-right: 2px solid #000000 !important;
        border-bottom: 2px solid #000000 !important;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
        color: #000000 !important;
    }

    /* =================================
       UI 卡片設計
       ================================= */
    /* 頂部資訊卡 */
    .header-card {
        background: white; padding: 20px 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;
        border: 2px solid #000000;
    }
    .header-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .header-time { font-size: 3rem; font-weight: 900; color: #000000; line-height: 1; }
    .header-day { font-size: 1.2rem; color: #000000; margin-left: 10px; margin-top: 15px; font-weight: bold;}
    .header-route { font-size: 1.3rem; font-weight: 900; color: #000000; margin-top: 10px; }
    
    /* 行程卡片 */
    .timeline-wrapper { position: relative; padding-left: 10px; margin-top: 20px;}
    .timeline-line {
        position: absolute; left: 69px; top: 0; bottom: 0; width: 3px; background: #000000; z-index: 0;
    }
    .trip-card {
        background: white; border-radius: 12px; padding: 15px;
        border-left: 6px solid #000; border: 1px solid #000; border-left-width: 6px;
        margin-bottom: 15px; position: relative; z-index: 1;
    }
    .card-title { font-size: 1.2rem; font-weight: 900; color: #000; margin: 0; }
    .card-price { background: #fff; color: #000; padding: 2px 8px; border: 1px solid #000; font-weight: 900; font-size: 0.9rem;}
    .card-loc a { color: #000; text-decoration: underline; font-weight: bold; font-size: 1rem;}
    .card-note { font-size: 0.95rem; color: #000; margin-top: 6px; font-weight: 500;}
    .time-col { font-size: 1.2rem; font-weight: 900; color: #000; text-align: right; padding-right: 10px; }
    .timeline-dot { width: 14px; height: 14px; background: white; border: 4px solid #000; border-radius: 50%; margin-top: 5px; position: relative; z-index: 2; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 側邊欄設定
# -------------------------------------
with st.sidebar:
    st.title("⚙️ 行程設定")
    start_date = st.date_input("📅 出發日期", value=datetime.today())
    trip_days_count = st.number_input("🔢 旅遊天數", min_value=1, max_value=30, value=5)
    st.divider()
    is_edit_mode = st.toggle("✏️ 啟用編輯模式", value=False)
    if is_edit_mode:
        st.warning("編輯模式已開啟")

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

# 確保每一天都有資料結構
for d in range(1, trip_days_count + 1):
    if d not in st.session_state.trip_data:
        st.session_state.trip_data[d] = []

# -------------------------------------
# 5. 主畫面渲染
# -------------------------------------
day_options = list(range(1, trip_days_count + 1))
selected_day_num = st.radio(
    "選擇天數", day_options, 
    index=1 if trip_days_count >=2 else 0,
    format_func=lambda x: f"Day {x}", 
    horizontal=True,
    label_visibility="collapsed"
)

# 日期計算
current_date_obj = start_date + timedelta(days=selected_day_num - 1)
date_str = current_date_obj.strftime("%m/%d")
week_days_ch = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
week_day_str = week_days_ch[int(current_date_obj.strftime("%w"))]

current_items = st.session_state.trip_data[selected_day_num]
total_cost = sum(i['cost'] for i in current_items)

# Header
header_html = f"""
<div class="header-card">
    <div class="header-top">
        <div style="display:flex;">
            <div class="header-time">{date_str}</div>
            <div class="header-day">{week_day_str}</div>
        </div>
        <div class="weather-box">
            <div class="weather-temp">12°</div>
            <div class="weather-desc">舒適涼爽</div>
        </div>
    </div>
    <div class="header-route">行程概覽 Day {selected_day_num}</div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

st.markdown(f"**Day {selected_day_num} 預算統計：¥{total_cost:,}**")

# 新增行程按鈕
if is_edit_mode:
    if st.button("➕ 新增一筆行程", type="primary", use_container_width=True):
        new_id = int(datetime.now().timestamp())
        st.session_state.trip_data[selected_day_num].append({
            "id": new_id, "time": "00:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": ""
        })
        st.rerun()

cat_colors = {"food": "#FF6B6B", "trans": "#4ECDC4", "stay": "#5E548E", "play": "#FFD93D", "other": "#95A5A6"}

st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)

if not current_items:
    st.info("😴 今天尚未安排行程")

current_items.sort(key=lambda x: x['time'])

for index, item in enumerate(current_items):
    c1, c2, c3 = st.columns([1, 0.4, 5])
    
    with c1:
        st.markdown(f'<div class="time-col">{item["time"]}</div>', unsafe_allow_html=True)
    
    with c2:
        color = cat_colors.get(item.get("cat", "other"), "#000")
        st.markdown(f'<div class="dot-col"><div class="timeline-dot" style="border-color:{color}"></div></div>', unsafe_allow_html=True)
    
    with c3:
        if is_edit_mode:
            # 編輯模式：使用 Expander，這次標題條已修復為淺灰底黑字
            with st.expander(f"📝 {item['title']}", expanded=True):
                c_title, c_del = st.columns([4, 1])
                with c_title:
                    # 注意：這裡的 label 已經透過 CSS div[data-testid="stWidgetLabel"] 修復為黑色
                    new_title = st.text_input("行程標題", item['title'], key=f"t_{item['id']}")
                with c_del:
                    if st.button("🗑️", key=f"del_{item['id']}", help="刪除"):
                        st.session_state.trip_data[selected_day_num].pop(index)
                        st.rerun()
                
                c_a, c_b = st.columns(2)
                item['time'] = c_a.text_input("時間 (HH:MM)", item['time'], key=f"tm_{item['id']}")
                item['cost'] = c_b.number_input("金額 (¥)", value=item['cost'], step=100, key=f"c_{item['id']}")
                item['loc'] = st.text_input("地點 (Google Maps)", item['loc'], key=f"l_{item['id']}")
                item['note'] = st.text_input("備註", item['note'], key=f"n_{item['id']}")
                item['title'] = new_title
        else:
            border_color = cat_colors.get(item.get("cat", "other"), "#000")
            price_html = f'<div class="card-price">¥{item["cost"]:,}</div>' if item["cost"] > 0 else ""
            loc_link = f'https://www.google.com/maps/search/?api=1&query={item["loc"]}'
            loc_html = f'<div class="card-loc"><a href="{loc_link}" target="_blank">📍 {item["loc"]}</a></div>' if item['loc'] else ""
            note_html = f'<div class="card-note">{item["note"]}</div>' if item["note"] else ""
            
            full_html = (
                f'<div class="trip-card" style="border-left-color: {border_color};">'
                f'<div class="card-content-row"><div class="card-title">{item["title"]}</div>{price_html}</div>'
                f'{loc_html}{note_html}</div>'
            )
            st.markdown(full_html, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
