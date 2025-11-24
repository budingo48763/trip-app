import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="旅日小幫手 Pro Max 🇯🇵", page_icon="🎌", layout="centered")

# -------------------------------------
# 2. CSS 樣式
# -------------------------------------
# 注意：這裡的 HTML 必須靠左對齊，不能有縮排
st.markdown("""
<style>
/* 全域設定 */
.stApp { 
    font-family: 'Helvetica Neue', Helvetica, 'Microsoft JhengHei', Arial, sans-serif; 
    background-color: #F9F9F9;
}

/* 標題區塊 */
.header-container {
    padding: 20px;
    text-align: center;
    background: white;
    border-radius: 0 0 20px 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}
.main-title { font-size: 1.8rem; font-weight: 800; color: #333; }
.sub-title { font-size: 0.9rem; color: #E63946; font-weight: 600; letter-spacing: 1px; }

/* 行程卡片 CSS */
.timeline-wrapper { position: relative; padding-left: 30px; margin-top: 10px; height: 100%; }
.timeline-line {
    position: absolute; left: 10px; top: 10px; bottom: -30px;
    width: 2px; background-color: #DDD; z-index: 0;
}
.timeline-dot {
    position: absolute; left: 4px; top: 20px;
    width: 14px; height: 14px; border-radius: 50%;
    background-color: #E63946; border: 3px solid white;
    box-shadow: 0 0 0 1px #E63946; z-index: 1;
}

/* 景點卡片 */
.event-card {
    background-color: #ffffff; border-radius: 12px;
    margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    overflow: hidden; border: 1px solid #f0f0f0; display: flex;
}
.card-img { width: 100px; height: 100px; object-fit: cover; }
.card-text { padding: 12px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
.time-badge { font-size: 0.8rem; font-weight: bold; color: #E63946; background: #FFF0F1; padding: 2px 8px; border-radius: 4px; }
.event-title { font-size: 1.1rem; font-weight: 700; color: #333; margin: 5px 0; }
.event-meta { font-size: 0.85rem; color: #888; display: flex; justify-content: space-between; }
.cost-tag { color: #555; font-weight: bold; }

/* 交通卡片 */
.transport-card {
    background-color: #F4F7F6; border-radius: 8px; padding: 12px;
    margin-bottom: 20px; border-left: 4px solid #4ECDC4;
    color: #555; font-size: 0.9rem; display: flex; align-items: center; gap: 10px;
}

/* 須知卡片 */
.info-box {
    background: white; padding: 15px; border-radius: 10px;
    border-left: 5px solid #E63946; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    margin-bottom: 10px;
}
.info-title { font-weight: bold; font-size: 1.1rem; color: #333; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------
# 3. 初始化資料
# -------------------------------------
if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [
            {"id": 101, "type": "transport", "time": "08:00", "title": "移動：名古屋 ➔ 上諏訪", "detail": "JR 特急 (信濃號)", "cost": 5000, "note": "記得帶車票"},
            {"id": 102, "type": "spot", "time": "10:30", "title": "Hotel Beni Ya", "location": "紅屋飯店", "image": "https://lh3.googleusercontent.com/p/AF1QipN3-vF0q6P2z4wJ-5s2x6v-9s2x6v-9s2x6v/w200-h200-k-no", "cost": 0, "cat": "住宿", "note": "寄放行李"},
            {"id": 103, "type": "spot", "time": "11:30", "title": "午餐：鰻魚飯", "location": "古色古香名店", "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Hitsumabushi_by_sakchored.jpg/640px-Hitsumabushi_by_sakchored.jpg", "cost": 2000, "cat": "餐飲", "note": "需排隊"},
            {"id": 105, "type": "spot", "time": "18:00", "title": "晚餐：Izumiya", "location": "いずみ屋", "image": "", "cost": 1500, "cat": "餐飲", "note": "影片中的晚餐"}
        ]
    }

default_packing_list = {
    "必備證件": {"護照 (效期6個月以上)": False, "網卡 / Wi-Fi 機": False, "日幣現金 / 信用卡": False, "VJW 入境 QR Code": False},
    "電子產品": {"手機 / 充電線": False, "行動電源 (需隨身帶)": False, "轉接頭 (日本雙孔扁插)": False, "耳機": False},
    "衣物穿搭": {"換洗衣物": False, "睡衣 / 貼身衣物": False, "好走的鞋子": False, "帽子 / 墨鏡": False},
    "生活用品": {"牙刷 / 牙膏": False, "保養品 / 化妝品": False, "常備藥品 (感冒/腸胃)": False, "塑膠袋 (裝髒衣)": False}
}

if "packing_list" not in st.session_state:
    st.session_state.packing_list = default_packing_list

# -------------------------------------
# 4. 側邊欄導航
# -------------------------------------
with st.sidebar:
    st.title("導航選單")
    page = st.radio("前往", ["📅 行程規劃", "🎒 行前準備"], index=0)
    st.divider()
    if page == "📅 行程規劃":
        start_date = st.date_input("出發日期", value=datetime.today())

# -------------------------------------
# 5. 頁面邏輯
# -------------------------------------

# === 頁面 A: 行程規劃 ===
if page == "📅 行程規劃":
    # Header HTML 也必須靠左
    st.markdown(f"""
<div class="header-container">
    <div class="main-title">Nagoya Trip</div>
    <div class="sub-title">{start_date.strftime('%Y/%m/%d')} • Day 1</div>
</div>
""", unsafe_allow_html=True)

    items = st.session_state.trip_data[1]

    for item in items:
        col_timeline, col_card = st.columns([0.1, 0.9])
        
        with col_timeline:
            st.markdown('<div class="timeline-wrapper"><div class="timeline-line"></div><div class="timeline-dot"></div></div>', unsafe_allow_html=True)
            
        with col_card:
            if item["type"] == "transport":
                # === 修正重點：字串內容全部靠左，移除所有縮排 ===
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

            else:
                img_html = f'<img src="{item["image"]}" class="card-img">' if item["image"] else ''
                # === 修正重點：字串內容全部靠左，移除所有縮排 ===
                st.markdown(f"""
<div class="event-card">
    {img_html}
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
""", unsafe_allow_html=True)

# === 頁面 B: 行前準備 ===
elif page == "🎒 行前準備":
    st.markdown('<div class="header-container"><div class="main-title">行前準備 Check List</div></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ℹ️ 出國須知", "✅ 行李清單"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
<div class="info-box">
    <div class="info-title">⚡ 電壓與插座</div>
    日本電壓為 100V，插座為雙孔扁插（與台灣相同）。<br>
    大部分台灣電器可直接使用，唯需注意筆電三孔插頭需轉接。
</div>
<div class="info-box">
    <div class="info-title">🚑 緊急聯絡</div>
    報警：110 <br>
    火警/救護車：119 <br>
    外交部旅外急難救助：+81-3-3280-7917
</div>
""", unsafe_allow_html=True)
        with col2:
            st.markdown("""
<div class="info-box">
    <div class="info-title">🚰 飲水與小費</div>
    自來水可生飲（建議飯店煮沸）。<br>
    日本<b>無小費文化</b>，結帳時金額即為總價。
</div>
<div class="info-box">
    <div class="info-title">💴 消費與退稅</div>
    消費稅 10%。<br>
    同日同一店家消費滿 ¥5,000 (未稅) 可辦理退稅。
</div>
""", unsafe_allow_html=True)
            
        st.info("💡 小撇步：把護照影本和證件照存一份在手機雲端，以備不時之需。")

    with tab2:
        total_items = sum(len(v) for v in st.session_state.packing_list.values())
        checked_items = sum(sum(v.values()) for v in st.session_state.packing_list.values())
        progress = checked_items / total_items if total_items > 0 else 0
        
        st.markdown(f"#### 🎒 打包進度：{int(progress*100)}%")
        st.progress(progress)
        
        if progress == 1.0:
            st.balloons()
            st.success("太棒了！行李準備完成，準備出發！ ✈️")

        st.markdown("---")
        
        for category, items in st.session_state.packing_list.items():
            st.markdown(f"##### {category}")
            cols = st.columns(2)
            for i, (item_name, is_checked) in enumerate(items.items()):
                col_idx = i % 2
                key = f"pack_{category}_{item_name}"
                def update_state(k=key, cat=category, name=item_name):
                    st.session_state.packing_list[cat][name] = st.session_state[k]

                cols[col_idx].checkbox(item_name, value=is_checked, key=key, on_change=update_state)
            st.markdown("")
