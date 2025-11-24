import streamlit as st
from datetime import datetime

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="長野・名古屋之旅", page_icon="🗾", layout="centered")

# -------------------------------------
# 2. 自定義 CSS (強力修復版)
# -------------------------------------
st.markdown("""
    <style>
    /* 全局字體與背景 */
    .stApp { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #F8F9FA; }
    
    /* 隱藏 Streamlit 預設元素 */
    .stDeployButton {display:none;}
    header {visibility: hidden;}

    /* 頂部大標題區塊 (改用 Flexbox 避免重疊) */
    .header-card {
        background: white;
        padding: 20px 25px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        margin-bottom: 25px;
        border: 1px solid #eee;
    }
    .header-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .header-time { font-size: 3.5rem; font-weight: 800; color: #333; line-height: 1; letter-spacing: -1px; }
    .header-day { font-size: 1.2rem; color: #999; font-weight: 500; margin-left: 10px; margin-top: 15px;}
    .header-route { font-size: 1.4rem; font-weight: 700; color: #444; margin-top: 10px; display: flex; align-items: center; gap: 10px; }
    
    /* 天氣區塊 */
    .weather-box { text-align: right; }
    .weather-temp { font-size: 1.8rem; font-weight: 800; color: #333; }
    .weather-desc { font-size: 0.9rem; color: #888; background: #f0f0f0; padding: 2px 8px; border-radius: 6px; display: inline-block; margin-top: 4px; }

    /* Day 選擇器樣式優化 (隱藏圓點) */
    div[role="radiogroup"] { gap: 8px; overflow-x: auto; padding-bottom: 5px; }
    div[role="radiogroup"] label > div:first-child { display: none; } /* 隱藏 Radio 圓圈 */
    div[role="radiogroup"] label {
        background: white !important;
        border: 1px solid #eee;
        padding: 8px 16px !important;
        border-radius: 12px !important;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background: #333 !important;
        color: white !important;
        border-color: #333;
    }

    /* 時間軸樣式 */
    .timeline-wrapper { position: relative; padding-left: 10px; }
    .timeline-line {
        position: absolute; left: 84px; top: 0; bottom: 0;
        width: 2px; background: #E0E0E0; z-index: 0;
    }

    /* 卡片內容樣式 (避免 HTML 破圖的核心) */
    .trip-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border-left: 5px solid #ccc; /* 預設顏色 */
        width: 100%;
        margin-bottom: 20px;
        position: relative;
        z-index: 1;
    }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .card-title { font-size: 1.15rem; font-weight: 700; color: #222; margin: 0; }
    .card-price { background: #F3F4F6; color: #555; padding: 4px 8px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; }
    .card-loc { font-size: 0.9rem; color: #666; display: flex; align-items: center; gap: 5px; margin-bottom: 6px; }
    .card-loc a { color: #555; text-decoration: none; border-bottom: 1px dotted #999; }
    .card-note { font-size: 0.85rem; color: #999; font-style: italic; }
    
    /* 時間與圓點 */
    .time-display { font-size: 1.1rem; font-weight: 700; color: #444; text-align: right; margin-top: 15px; }
    .timeline-dot {
        width: 14px; height: 14px; background: white;
        border: 3px solid #FF5A5F; border-radius: 50%;
        margin: 18px auto 0 auto; position: relative; z-index: 2;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 初始化資料 (範例資料)
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
# 4. 頂部資訊卡 (修復版)
# -------------------------------------
# 日期與資料
days_map = {1: "週日", 2: "週一", 3: "週二", 4: "週三", 5: "週四", 6: "週五", 7: "週六"}

# Day 選擇器 (改用 Radio 但 CSS 已美化)
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

# Header HTML
st.markdown(f"""
<div class="header-card">
    <div class="header-top">
        <div style="display:flex;">
            <div class="header-time">11:35</div>
            <div class="header-day">{day_str}</div>
        </div>
        <div class="weather-box">
            <div class="weather-temp">12°</div>
            <div class="weather-desc">舒適涼爽</div>
        </div>
    </div>
    <div class="header-route">
        <span>名古屋</span> ✈️ <span>上諏訪</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------
# 5. 行程列表 (Timeline Fix)
# -------------------------------------
col_head1, col_head2 = st.columns([3, 1])
col_head1.caption(f"Day {selected_day} 行程 • 預算 ¥{total_cost:,}")
is_edit = col_head2.checkbox("編輯", value=False)

# 顏色對應
cat_colors = {
    "food": "#FF6B6B",   # 紅 (吃)
    "trans": "#4ECDC4",  # 青 (行)
    "stay": "#5E548E",   # 紫 (住)
    "play": "#FFD93D",   # 黃 (玩)
    "other": "#95A5A6"   # 灰 (其他)
}

st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div>', unsafe_allow_html=True)

if not current_items:
    st.info("😴 今天沒有行程")

for idx, item in enumerate(current_items):
    # 使用 columns 來切分：時間 | 圓點 | 卡片
    # 比例調整為 [1.2, 0.3, 5] 確保時間不換行，圓點居中，卡片最大
    c1, c2, c3 = st.columns([1.2, 0.3, 5])
    
    with c1:
        st.markdown(f'<div class="time-display">{item["time"]}</div>', unsafe_allow_html=True)
    
    with c2:
        # 圓點顏色跟隨類別
        dot_color = cat_colors.get(item.get("cat", "other"), "#999")
        st.markdown(f'<div class="timeline-dot" style="border-color: {dot_color};"></div>', unsafe_allow_html=True)
    
    with c3:
        if is_edit:
            # 編輯模式：使用 Expander 保持整潔
            with st.expander(f"📝 {item['title']}", expanded=True):
                new_title = st.text_input("標題", item['title'], key=f"t_{item['id']}")
                c_a, c_b = st.columns(2)
                new_time = c_a.text_input("時間", item['time'], key=f"tm_{item['id']}")
                new_cost = c_b.number_input("金額", value=item['cost'], step=100, key=f"c_{item['id']}")
                new_loc = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                
                if st.button("保存", key=f"s_{item['id']}"):
                    item.update({"title": new_title, "time": new_time, "cost": new_cost, "loc": new_loc})
                    st.rerun()
        else:
            # 瀏覽模式：純 HTML 卡片 (注意這裡的 f-string 結構已經簡化)
            border_color = cat_colors.get(item.get("cat", "other"), "#ccc")
            loc_html = f'<a href="https://www.google.com/maps/search/?api=1&query={item["loc"]}" target="_blank">{item["loc"]}</a>' if item['loc'] else "無地點"
            price_html = f'<div class="card-price">¥{item["cost"]:,}</div>' if item["cost"] > 0 else ""
            
            card_html = f"""
            <div class="trip-card" style="border-left-color: {border_color};">
                <div class="card-header">
                    <div class="card-title">{item['title']}</div>
                    {price_html}
                </div>
                <div class="card-loc">📍 {loc_html}</div>
                <div class="card-note">{item['note']}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
