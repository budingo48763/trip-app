import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import platform
import urllib.parse
import random

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="旅日小幫手 Pro Max 🇯🇵", page_icon="🎌", layout="centered")

# -------------------------------------
# 2. 進階 CSS (模仿影片中的時間軸與卡片設計)
# -------------------------------------
st.markdown("""
    <style>
    /* 全域字體設定 */
    .stApp { 
        font-family: 'Helvetica Neue', Helvetica, 'Microsoft JhengHei', Arial, sans-serif; 
        background-color: #F9F9F9;
    }
    
    /* 標題區塊 */
    .header-container {
        padding: 20px 0;
        text-align: center;
        background: white;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .main-title { font-size: 1.5rem; font-weight: 800; color: #333; margin: 0; }
    .sub-title { font-size: 0.9rem; color: #E63946; font-weight: 600; letter-spacing: 1px; }

    /* 時間軸容器 */
    .timeline-wrapper {
        position: relative;
        padding-left: 30px; /* 給左邊的時間軸線留空間 */
        margin-top: 10px;
    }
    
    /* 左側直條線 */
    .timeline-line {
        position: absolute;
        left: 10px;
        top: 10px;
        bottom: -20px;
        width: 2px;
        background-color: #DDD;
        z-index: 0;
    }

    /* 時間點 (圓點) */
    .timeline-dot {
        position: absolute;
        left: 4px; /* (Line left 10px) - (Dot width 14px / 2) + (Line width 2px / 2) */
        top: 20px;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background-color: #E63946;
        border: 3px solid white;
        box-shadow: 0 0 0 1px #E63946;
        z-index: 1;
    }

    /* 行程卡片本體 */
    .event-card {
        background-color: #ffffff;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        overflow: hidden; /* 讓圖片圓角正常顯示 */
        transition: transform 0.2s;
        border: 1px solid #f0f0f0;
    }
    
    /* 交通專用卡片樣式 */
    .transport-card {
        background-color: #F4F7F6;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 20px;
        border-left: 4px solid #4ECDC4;
        color: #555;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* 卡片內容佈局 */
    .card-content { display: flex; flex-direction: row; }
    
    /* 圖片區塊 */
    .card-img {
        width: 100px;
        height: 100px;
        object-fit: cover;
    }
    
    /* 文字區塊 */
    .card-text { padding: 12px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
    
    .time-badge { 
        font-size: 0.8rem; font-weight: bold; color: #E63946; 
        background: #FFF0F1; padding: 2px 8px; border-radius: 4px; display: inline-block; margin-bottom: 4px;
    }
    .event-title { font-size: 1.1rem; font-weight: 700; color: #333; margin: 0; }
    .event-meta { font-size: 0.85rem; color: #888; margin-top: 4px; display: flex; justify-content: space-between;}
    .cost-tag { color: #555; font-weight: bold; }
    
    /* 按鈕樣式微調 */
    div.stButton > button { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 初始化資料 (模擬影片中的情境)
# -------------------------------------
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            # 交通類型
            {
                "id": 101, "type": "transport", "time": "08:00", 
                "title": "移動：名古屋 ➔ 上諏訪", "detail": "JR 特急 (信濃號)", 
                "cost": 5000, "note": "記得帶車票"
            },
            # 景點類型 (含圖片)
            {
                "id": 102, "type": "spot", "time": "10:30", 
                "title": "寄放行李 / Hotel Beni Ya", "location": "紅屋飯店",
                "image": "https://lh3.googleusercontent.com/p/AF1QipN3-vF0q6P2z4wJ-5s2x6v-9s2x6v-9s2x6v/w200-h200-k-no", # 假圖
                "cost": 0, "cat": "住宿", "note": "租腳踏車"
            },
            {
                "id": 103, "type": "spot", "time": "11:30", 
                "title": "午餐：鰻魚飯", "location": "古色古香名店",
                "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Hitsumabushi_by_sakchored.jpg/640px-Hitsumabushi_by_sakchored.jpg",
                "cost": 2000, "cat": "餐飲", "note": "需排隊"
            },
            {
                "id": 104, "type": "spot", "time": "13:30", 
                "title": "高島城跡", "location": "諏訪護國神社",
                "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Takashima_Castle_Keep_Tower.jpg/640px-Takashima_Castle_Keep_Tower.jpg",
                "cost": 0, "cat": "景點", "note": "逛完去八劍神社"
            },
            {
                "id": 105, "type": "spot", "time": "18:00", 
                "title": "晚餐：Izumiya", "location": "いずみ屋",
                "image": "", # 無圖測試
                "cost": 1500, "cat": "餐飲", "note": "影片中的晚餐"
            }
        ]
    }

def get_map_link(query):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query) if query else "#"

# -------------------------------------
# 4. 側邊欄與設定
# -------------------------------------
with st.sidebar:
    st.title("⚙️ 設定")
    start_date = st.date_input("出發日期", value=datetime.today())
    is_edit_mode = st.toggle("✏️ 編輯模式", value=True)
    st.divider()
    
    # 預算統計 (小工具)
    total_budget = 0
    for day, items in st.session_state.trip_data.items():
        total_budget += sum(item.get('cost', 0) for item in items)
    st.metric("💰 總預算累積", f"¥{total_budget:,}")

# -------------------------------------
# 5. 主畫面渲染
# -------------------------------------
# 頂部 Header
st.markdown(f"""
    <div class="header-container">
        <div class="main-title">Nagoya & Suwa Trip</div>
        <div class="sub-title">{start_date.strftime('%Y/%m/%d')} • Day 1</div>
    </div>
""", unsafe_allow_html=True)

# 獲取當日資料
day_idx = 1 # 這裡簡化示範 Day 1
items = st.session_state.trip_data.get(day_idx, [])

# --- 新增行程區塊 (只有編輯模式顯示) ---
if is_edit_mode:
    with st.expander("➕ 新增行程 (一般/交通)", expanded=False):
        tab_spot, tab_trans = st.tabs(["🏛️ 一般景點", "🚄 交通移動"])
        
        with tab_spot:
            c1, c2 = st.columns([1, 2])
            s_time = c1.time_input("時間", value=datetime.now().time(), key="s_time")
            s_title = c2.text_input("名稱", placeholder="例：高島城", key="s_title")
            s_img = st.text_input("圖片網址 (選填)", placeholder="https://...", key="s_img")
            c3, c4 = st.columns(2)
            s_cost = c3.number_input("費用 (¥)", step=100, key="s_cost")
            s_note = c4.text_input("備註", key="s_note")
            if st.button("加入景點", type="primary"):
                new_item = {
                    "id": int(datetime.now().timestamp()), "type": "spot",
                    "time": s_time.strftime("%H:%M"), "title": s_title,
                    "location": s_title, "image": s_img, "cost": s_cost, "cat": "景點", "note": s_note
                }
                items.append(new_item)
                items.sort(key=lambda x: x['time'])
                st.rerun()

        with tab_trans:
            c1, c2 = st.columns([1, 2])
            t_time = c1.time_input("出發時間", key="t_time")
            t_route = c2.text_input("路線", placeholder="例：名古屋 ➔ 上諏訪", key="t_route")
            t_detail = st.text_input("交通方式", placeholder="例：JR 特急信濃號", key="t_detail")
            t_cost = st.number_input("車資 (¥)", step=100, key="t_cost")
            if st.button("加入交通"):
                new_item = {
                    "id": int(datetime.now().timestamp()), "type": "transport",
                    "time": t_time.strftime("%H:%M"), "title": f"移動：{t_route}",
                    "detail": t_detail, "cost": t_cost, "note": ""
                }
                items.append(new_item)
                items.sort(key=lambda x: x['time'])
                st.rerun()

# --- 時間軸渲染 ---
st.write("") # Spacer

for i, item in enumerate(items):
    # 建立時間軸結構
    col_timeline_left, col_card_right = st.columns([0.1, 0.9])
    
    # 1. 左側線條與圓點 (純 HTML/CSS)
    with col_timeline_left:
        # 使用空的 markdown 佔位，實際樣式由上面的 CSS .timeline-line 和 .timeline-dot 控制
        # 這裡需要一個 wrap div
        st.markdown(f"""
        <div class="timeline-wrapper" style="height: 100%;">
            <div class="timeline-line"></div>
            <div class="timeline-dot"></div>
        </div>
        """, unsafe_allow_html=True)
    
    # 2. 右側卡片內容
    with col_card_right:
        
        # === A. 交通卡片樣式 ===
        if item.get("type") == "transport":
            st.markdown(f"""
            <div class="transport-card">
                <div style="font-size:1.5rem;">🚄</div>
                <div style="flex:1;">
                    <div style="font-weight:bold;">{item['time']} {item['title']}</div>
                    <div style="font-size:0.8rem; color:#666;">{item.get('detail', '')}</div>
                </div>
                <div style="font-weight:bold; color:#4ECDC4;">¥{item['cost']:,}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # === B. 一般景點卡片樣式 (模仿影片中的圖文並茂) ===
        else:
            image_html = f'<img src="{item["image"]}" class="card-img">' if item.get("image") else ''
            # 如果沒有圖片，調整 padding
            text_style = "padding: 12px; flex: 1;" if not item.get("image") else "padding: 12px; flex: 1;"
            
            card_html = f"""
            <div class="event-card">
                <div class="card-content">
                    {image_html}
                    <div class="card-text">
                        <div>
                            <span class="time-badge">{item['time']}</span>
                            <div class="event-title">{item['title']}</div>
                            <div style="font-size:0.8rem; color:#aaa;">📍 {item['location']}</div>
                        </div>
                        <div class="event-meta">
                            <span>{item['note']}</span>
                            <span class="cost-tag">¥{item['cost']:,}</span>
                        </div>
                    </div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        # === 編輯/刪除按鈕 (僅在編輯模式) ===
        if is_edit_mode:
            c_edit, c_del, c_space = st.columns([1, 1, 6])
            with c_edit:
                with st.popover("✏️", help="編輯"):
                    new_cost = st.number_input(f"修改金額 ({item['title']})", value=item['cost'], key=f"c_{item['id']}")
                    if st.button("儲存", key=f"save_{item['id']}"):
                        item['cost'] = new_cost
                        st.rerun()
            with c_del:
                if st.button("🗑️", key=f"del_{item['id']}"):
                    items.pop(i)
                    st.rerun()

# 底部空白
st.markdown("<br><br>", unsafe_allow_html=True)