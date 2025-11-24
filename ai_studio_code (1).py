import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="長野・名古屋之旅", page_icon="🗾", layout="centered")

# -------------------------------------
# 2. 自定義 CSS (核心樣式還原)
# -------------------------------------
st.markdown("""
    <style>
    /* 全局字體 */
    .stApp { font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'LiHei Pro', sans-serif; background-color: #F8F9FA; }
    
    /* 頂部大標題區塊 */
    .header-container {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        position: relative;
    }
    .big-time { font-size: 3rem; font-weight: 700; color: #333; line-height: 1; }
    .week-day { font-size: 1.2rem; color: #888; font-weight: 400; writing-mode: vertical-rl; position: absolute; top: 25px; left: 140px;}
    .route-text { font-size: 1.5rem; font-weight: 600; color: #333; margin-top: 10px; }
    .weather-badge {
        position: absolute; top: 20px; right: 20px;
        text-align: center; color: #555;
    }
    .temp-text { font-size: 1.5rem; font-weight: bold; }
    
    /* 日期導航條 */
    .day-nav { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 10px; }
    .day-btn {
        background: white; border: 1px solid #ddd; border-radius: 8px;
        padding: 8px 15px; min-width: 60px; text-align: center; cursor: pointer;
        color: #888; font-size: 0.9rem;
    }
    .day-btn.active { background: #A44A4A; color: white; border-color: #A44A4A; font-weight: bold; }
    
    /* 時間軸樣式 (Timeline) */
    .timeline-container {
        position: relative;
        padding-left: 20px;
        margin-top: 20px;
    }
    /* 垂直線 */
    .timeline-line {
        position: absolute;
        left: 26px;
        top: 10px;
        bottom: -20px;
        width: 2px;
        background-color: #E0E0E0;
        z-index: 0;
    }
    
    /* 行程卡片 */
    .itinerary-item {
        display: flex;
        margin-bottom: 25px;
        position: relative;
        z-index: 1;
    }
    .time-col {
        width: 60px;
        text-align: right;
        padding-right: 15px;
        font-weight: 600;
        color: #333;
        font-size: 1.1rem;
        padding-top: 5px;
    }
    .dot-col {
        width: 20px;
        display: flex;
        justify-content: center;
        padding-top: 10px;
    }
    .dot {
        width: 12px; height: 12px;
        background-color: #A44A4A; /* 深紅色圓點 */
        border-radius: 50%;
        border: 2px solid white;
        box-shadow: 0 0 0 1px #A44A4A;
    }
    .content-card {
        flex: 1;
        background: white;
        border-radius: 10px;
        padding: 12px 15px;
        margin-left: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 4px solid #A44A4A; /* 分類顏色 */
    }
    .item-title { font-size: 1.1rem; font-weight: bold; color: #333; margin-bottom: 4px; }
    .item-sub { font-size: 0.9rem; color: #666; margin-bottom: 4px; }
    .item-cost { 
        display: inline-block; 
        background: #f0f0f0; 
        color: #333; 
        padding: 2px 8px; 
        border-radius: 4px; 
        font-size: 0.85rem; 
        font-weight: 600;
        float: right;
    }
    .map-link { color: #A44A4A; text-decoration: none; font-size: 0.85rem; }
    
    /* 隱藏 Streamlit 原生元素 */
    .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 初始化資料 (還原影片中的 Day 2 行程)
# -------------------------------------
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "time": "11:35", "title": "抵達名古屋", "loc": "中部國際機場", "cost": 0, "cat": "trans"},
        ],
        2: [ # 影片中的主要內容
            {"id": 201, "time": "07:00", "title": "起床 & 早餐", "loc": "相鐵FRESA INN", "cost": 0, "cat": "stay", "note": "晨跑"},
            {"id": 202, "time": "08:00", "title": "移動：名古屋 → 上諏訪", "loc": "JR 特急 (信濃號)", "cost": 0, "cat": "trans", "note": "指定席"},
            {"id": 203, "time": "10:30", "title": "放行李 / 租腳踏車", "loc": "ホテル紅や (Hotel Beni Ya)", "cost": 0, "cat": "stay", "note": "寄放行李 -> 租車"},
            {"id": 204, "time": "11:30", "title": "午餐：鰻魚飯", "loc": "古色古香名店", "cost": 2000, "cat": "food", "note": "ねばし"},
            {"id": 205, "time": "13:30", "title": "高島城跡", "loc": "高島城", "cost": 0, "cat": "play", "note": "諏訪護國神社 -> 八劍神社"},
            {"id": 206, "time": "15:30", "title": "Check-in", "loc": "ホテル紅や", "cost": 0, "cat": "stay", "note": "入住手續"},
            {"id": 207, "time": "18:00", "title": "晚餐：いずみ屋", "loc": "Izumiya", "cost": 1500, "cat": "food", "note": "居酒屋"},
            {"id": 208, "time": "19:00", "title": "超市採購", "loc": "TSURUYA Kamisuwa", "cost": 420, "cat": "shop", "note": "飲料跟酒"},
        ],
        3: [], 4: [], 5: [], 6: [], 7: []
    }

# -------------------------------------
# 4. 側邊欄與狀態控制
# -------------------------------------
with st.sidebar:
    st.header("⚙️ 設定")
    # 編輯模式開關
    is_edit_mode = st.toggle("✏️ 編輯模式", value=False)
    st.write("開啟後可修改行程與金額")
    
    st.divider()
    st.caption("長野・名古屋之旅")

# -------------------------------------
# 5. 主畫面 - 頂部資訊卡 (Header)
# -------------------------------------
# 計算 Day 2 是週幾 (假設 Day 1 是週日)
days_jp = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
current_time_str = datetime.now().strftime("%H:%M") # 模擬影片左上角時間

# 選擇天數 (模擬橫向 Tabs)
st.write("") # Spacer
day_cols = st.columns([1,1,1,1,1,1,1])
selected_day = st.session_state.get("selected_day", 2)

# 渲染日期按鈕 (簡單用 Streamlit 按鈕模擬)
# 為了美觀，我們用 radio 的橫向模式來控制天數
selected_day = st.radio("選擇天數", [1,2,3,4,5,6,7], index=1, horizontal=True, format_func=lambda x: f"Day {x}", label_visibility="collapsed")

# 獲取當日資料
current_items = st.session_state.trip_data[selected_day]
daily_cost = sum(item['cost'] for item in current_items)

# 頂部 HTML 渲染
header_html = f"""
<div class="header-container">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
            <div class="big-time">11:35</div>
            <div class="route-text">名古屋 🚄 上諏訪</div>
        </div>
        <div class="weather-badge">
            <div class="temp-text">12°</div>
            <div style="font-size:0.8rem;">舒適涼爽</div>
        </div>
    </div>
    <div style="position:absolute; top:25px; left:120px; font-size:1.2rem; color:#888;">{days_jp[selected_day % 7]}</div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# -------------------------------------
# 6. 行程列表 (Timeline View)
# -------------------------------------

# 顯示工具列
col_tools1, col_tools2 = st.columns([3, 1])
with col_tools1:
    st.markdown(f"**Day {selected_day} 行程** <span style='color:#888; margin-left:10px; font-size:0.9rem;'>預算 ¥{daily_cost:,}</span>", unsafe_allow_html=True)
with col_tools2:
    if is_edit_mode:
        if st.button("➕ 新增", use_container_width=True):
             # 簡單新增邏輯
             new_id = int(datetime.now().timestamp())
             st.session_state.trip_data[selected_day].append(
                 {"id": new_id, "time": "00:00", "title": "新行程", "loc": "", "cost": 0, "cat": "other", "note": ""}
             )
             st.rerun()

st.markdown('<div class="timeline-container"><div class="timeline-line"></div>', unsafe_allow_html=True)

if not current_items:
    st.info("本日尚無行程，請點擊編輯模式新增。")

# 排序行程
current_items.sort(key=lambda x: x['time'])

for index, item in enumerate(current_items):
    # 決定卡片左邊框顏色 (簡單分類)
    cat_colors = {"food": "#FF6B6B", "trans": "#4ECDC4", "stay": "#5E548E", "play": "#FFD93D", "shop": "#FF8C42"}
    color = cat_colors.get(item.get("cat", "other"), "#ccc")
    
    # 建立一列 Layout
    col_layout = st.columns([1.5, 0.5, 6]) # 時間, 點, 卡片內容
    
    with col_layout[0]: # 時間
         st.markdown(f"<div class='time-col'>{item['time']}</div>", unsafe_allow_html=True)
    
    with col_layout[1]: # 圓點
         st.markdown(f"<div class='dot-col'><div class='dot'></div></div>", unsafe_allow_html=True)
         
    with col_layout[2]: # 卡片內容
        if is_edit_mode:
            # 編輯模式：顯示編輯器
            with st.expander(f"📝 {item['title']}", expanded=False):
                with st.container():
                    c1, c2 = st.columns(2)
                    new_title = c1.text_input("標題", item['title'], key=f"t_{item['id']}")
                    new_time = c2.text_input("時間", item['time'], key=f"tm_{item['id']}")
                    new_loc = st.text_input("地點", item['loc'], key=f"l_{item['id']}")
                    
                    # 記帳功能 (模仿影片輸入金額)
                    new_cost = st.number_input("金額 (¥)", value=item['cost'], step=100, key=f"c_{item['id']}")
                    new_note = st.text_area("備註", item['note'], key=f"n_{item['id']}")
                    
                    col_act1, col_act2 = st.columns(2)
                    if col_act1.button("保存", key=f"save_{item['id']}", type="primary"):
                        item['title'] = new_title
                        item['time'] = new_time
                        item['loc'] = new_loc
                        item['cost'] = int(new_cost)
                        item['note'] = new_note
                        st.rerun()
                    if col_act2.button("刪除", key=f"del_{item['id']}"):
                        st.session_state.trip_data[selected_day].pop(index)
                        st.rerun()
        else:
            # 瀏覽模式：顯示卡片
            cost_html = f"<div class='item-cost'>¥{item['cost']:,}</div>" if item['cost'] > 0 else ""
            loc_link = f"https://www.google.com/maps/search/?api=1&query={item['loc']}" if item['loc'] else "#"
            
            card_html = f"""
            <div class="content-card" style="border-left-color: {color};">
                <div style="display:flex; justify-content:space-between;">
                    <div class="item-title">{item['title']}</div>
                    {cost_html}
                </div>
                <div class="item-sub">📍 <a href="{loc_link}" target="_blank" class="map-link">{item['loc'] or '未設定地點'}</a></div>
                <div style="font-size:0.8rem; color:#888; margin-top:5px;">{item['note']}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # End timeline container

# -------------------------------------
# 7. 底部統計
# -------------------------------------
if not is_edit_mode:
    st.markdown("---")
    st.caption(f"📊 目前總花費: ¥{daily_cost:,}")
