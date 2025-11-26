import streamlit as st
from datetime import datetime, timedelta
import urllib.parse
import time
import pandas as pd
import random
import json
from PIL import Image

# --- 套件匯入檢查 ---
CLOUD_AVAILABLE = False
MAP_AVAILABLE = False
GEMINI_AVAILABLE = False

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    CLOUD_AVAILABLE = True
except ImportError: pass

try:
    import folium
    from streamlit_folium import st_folium
    from geopy.geocoders import Nominatim
    MAP_AVAILABLE = True
except ImportError: pass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError: pass

# -------------------------------------
# 1. 系統設定
# -------------------------------------
st.set_page_config(page_title="2026 旅程規劃 Pro", page_icon="✈️", layout="centered", initial_sidebar_state="collapsed")

THEMES = {
    "⛩️ 京都緋紅 (預設)": {"bg": "#FDFCF5", "card": "#FFFFFF", "text": "#2B2B2B", "primary": "#8E2F2F", "secondary": "#D6A6A6", "sub": "#666666"},
    "🌫️ 莫蘭迪·霧藍": {"bg": "#F0F4F8", "card": "#FFFFFF", "text": "#243B53", "primary": "#486581", "secondary": "#BCCCDC", "sub": "#627D98"},
    "🌿 莫蘭迪·鼠尾草": {"bg": "#F1F5F1", "card": "#FFFFFF", "text": "#2C3E2C", "primary": "#5F7161", "secondary": "#AFC0B0", "sub": "#506050"},
    "🍂 莫蘭迪·焦糖奶茶": {"bg": "#FAF6F1", "card": "#FFFFFF", "text": "#4A3B32", "primary": "#9C7C64", "secondary": "#E0D0C5", "sub": "#7D6556"}
}

# -------------------------------------
# 2. 核心函數
# -------------------------------------
def analyze_receipt_image(image_file):
    if not GEMINI_AVAILABLE: return [{"name":"模擬商品","price":100}]
    if "GEMINI_API_KEY" not in st.secrets: return [{"name":"請設API Key","price":0}]
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        img = Image.open(image_file)
        prompt = "分析收據，列出商品名稱與金額(整數)。翻譯成繁體中文。忽略小計稅金。回傳JSON Array:[{'name':'A','price':100}]。無Markdown。"
        
        # 自動選模型
        model_name = 'models/gemini-1.5-flash'
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini-2.0' in m.name: model_name = m.name; break
        except: pass
        
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content([prompt, img])
        txt = resp.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(txt)
        return data if isinstance(data, list) else [data]
    except: return [{"name":"分析失敗","price":0}]

@st.cache_data
def get_lat_lon(name):
    if not MAP_AVAILABLE: return None
    try:
        loc = Nominatim(user_agent="trip_app_v99").geocode(name)
        return (loc.latitude, loc.longitude) if loc else None
    except: return None

def get_cloud_client():
    if not CLOUD_AVAILABLE: return None
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
        return gspread.authorize(creds)
    except: return None

def cloud_save(data):
    c = get_cloud_client()
    if c:
        try: c.open("TripPlanDB").sheet1.update_cell(1, 1, json.dumps(data, default=str)); return True, "成功"
        except Exception as e: return False, str(e)
    return False, "連線失敗"

def cloud_load():
    c = get_cloud_client()
    if c:
        try: return c.open("TripPlanDB").sheet1.cell(1, 1).value
        except: return None
    return None

class Weather:
    ICONS = {"Sunny":"☀️", "Cloudy":"☁️", "Rainy":"🌧️", "Snowy":"❄️"}
    @staticmethod
    def get(loc, date):
        random.seed(f"{loc}{date}")
        cond = random.choice(["Sunny", "Cloudy", "Rainy"])
        desc = {"Sunny":"晴","Cloudy":"陰","Rainy":"雨","Snowy":"雪"}
        return {"high":25, "low":18, "icon":Weather.ICONS[cond], "desc":desc[cond], "raw":cond}

def get_packing(trip, start):
    recs = set()
    has_rain = False
    for day, items in trip.items():
        w = Weather.get(items[0]['loc'] if items else "City", start + timedelta(days=day-1))
        if w['raw'] in ["Rainy","Snowy"]: has_rain = True
    if has_rain: recs.add("☔ 雨具")
    recs.add("🧢 防曬")
    return list(recs)

def process_excel(file):
    try:
        df = pd.read_excel(file)
        new_data = {}
        for _, row in df.iterrows():
            d = int(row['Day'])
            if d not in new_data: new_data[d] = []
            new_data[d].append({
                "id": int(time.time()*1000)+_, "time": str(row['Time']), "title": str(row['Title']),
                "loc": str(row.get('Location','')), "cost": int(row.get('Cost',0)), 
                "note": str(row.get('Note','')), "expenses": [], "trans_mode": "📍", "trans_min": 30
            })
        st.session_state.trip_data = new_data
        st.session_state.trip_days_count = max(new_data.keys())
        st.rerun()
    except: st.error("格式錯誤")

# -------------------------------------
# 3. 初始化
# -------------------------------------
if "trip_title" not in st.session_state: st.session_state.trip_title = "2026 阪京之旅"
if "exchange_rate" not in st.session_state: st.session_state.exchange_rate = 0.215
if "trip_days_count" not in st.session_state: st.session_state.trip_days_count = 5
if "target_country" not in st.session_state: st.session_state.target_country = "日本"
if "selected_theme_name" not in st.session_state: st.session_state.selected_theme_name = "⛩️ 京都緋紅 (預設)"
if "start_date" not in st.session_state: st.session_state.start_date = datetime(2026, 1, 17)
if "wishlist" not in st.session_state: st.session_state.wishlist = [{"id":999, "title":"HARBS", "loc":"京都", "note":"蛋糕"}]
if "shopping_list" not in st.session_state: st.session_state.shopping_list = pd.DataFrame(columns=["對象","商品","預算","已買"])

cur = THEMES[st.session_state.selected_theme_name]

if "trip_data" not in st.session_state:
    st.session_state.trip_data = {
        1: [{"id":101, "time":"10:00", "title":"抵達", "loc":"關西機場", "cost":0, "note":"入境", "expenses":[], "trans_mode":"🚆", "trans_min":45}],
        2: [{"id":201, "time":"09:00", "title":"清水寺", "loc":"清水寺", "cost":400, "note":"", "expenses":[], "trans_mode":"🚶", "trans_min":20}],
        3:[], 4:[], 5:[]
    }

if "flight_info" not in st.session_state:
    st.session_state.flight_info = {"out":{"date":"1/17","code":"JX821","dep":"10:00","arr":"13:30","d":"TPE","a":"KIX"}, "in":{"date":"1/22","code":"JX822","dep":"15:00","arr":"17:10","d":"KIX","a":"TPE"}}

if "hotel_info" not in st.session_state:
    st.session_state.hotel_info = [{"id":1, "name":"KOKO HOTEL", "range":"D1-D3", "date":"1/17-1/19", "addr":"京都", "link":""}]

if "checklist" not in st.session_state:
    st.session_state.checklist = {"證件":{"護照":False}, "電子":{"網卡":False}, "衣物":{"外套":False}}

PHRASES = {
    "日本": {"招呼":[("你好","こんにちは"),("謝謝","ありがとう")], "購物":[("免稅","免税OK?"),("多少錢","いくら?")]},
    "韓國": {"招呼":[("你好","안녕하세요"),("謝謝","감사합니다")], "購物":[("多少錢","얼마예요"),("打折","깎아 주세요")]},
    "泰國": {"招呼":[("你好","Sawasdee"),("謝謝","Khop khun")], "購物":[("多少錢","Tao rai"),("太貴","Paeng mak")]}
}
# 預設回退
if st.session_state.target_country not in PHRASES: PHRASES[st.session_state.target_country] = {"通用": [("你好","Hello")]}

# -------------------------------------
# 4. CSS (安全寫法)
# -------------------------------------
css_code = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&family=Inter:wght@400;600&display=swap');
.stApp { background-color: __BG__ !important; color: __TXT__ !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebarCollapsedControl"], footer { display: none !important; }
header[data-testid="stHeader"] { height: 0 !important; background: transparent !important; }
.apple-card {
    background: rgba(255, 255, 255, 0.95); border-radius: 18px; padding: 15px; margin-bottom: 0px;
    border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 4px 15px rgba(0,0,0,0.04);
}
.weather-box {
    background: linear-gradient(135deg, __PRI__ 0%, __TXT__ 150%); color: white;
    padding: 15px 20px; border-radius: 20px; margin-bottom: 20px;
    display: flex; align-items: center; justify-content: space-between;
}
.trans-box {
    background: #FFF; border-radius: 12px; padding: 8px 12px; margin: 5px 0 5px 50px;
    border: 1px solid #E0E0E0; display: flex; justify-content: space-between; align-items: center;
}
div[data-testid="stRadio"] > div { background-color: __SEC__; padding: 4px; border-radius: 12px; overflow-x: auto; flex-wrap: nowrap; }
div[data-testid="stRadio"] label[data-checked="true"] { background-color: __CARD__; color: __TXT__; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
input { color: __TXT__ !important; }
</style>
"""
# 替換變數
for k, v in [("__BG__", cur['bg']), ("__TXT__", cur['text']), ("__PRI__", cur['primary']), ("__SEC__", cur['secondary']), ("__CARD__", cur['card'])]:
    css_code = css_code.replace(k, v)
st.markdown(css_code, unsafe_allow_html=True)

# -------------------------------------
# 5. UI
# -------------------------------------
st.markdown(f'<div style="font-size:2rem;font-weight:900;text-align:center;color:{cur["text"]};">{st.session_state.trip_title}</div>', unsafe_allow_html=True)
st.markdown(f'<div style="text-align:center;color:{cur["sub"]};font-size:0.9rem;margin-bottom:20px;">{st.session_state.start_date.strftime("%Y/%m/%d")} 出發</div>', unsafe_allow_html=True)

with st.expander("⚙️ 設定"):
    st.session_state.trip_title = st.text_input("標題", st.session_state.trip_title)
    tn = st.selectbox("主題", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.selected_theme_name))
    if tn != st.session_state.selected_theme_name:
        st.session_state.selected_theme_name = tn
        st.rerun()
    c1, c2 = st.columns(2)
    st.session_state.start_date = c1.date_input("日期", st.session_state.start_date)
    st.session_state.trip_days_count = c2.number_input("天數", 1, 30, st.session_state.trip_days_count)
    st.session_state.target_country = st.selectbox("地區", ["日本", "韓國", "泰國", "台灣"])
    st.session_state.exchange_rate = st.number_input("匯率", value=st.session_state.exchange_rate, step=0.01)
    uf = st.file_uploader("匯入 Excel", type=["xlsx"])
    if uf and st.button("匯入"): process_excel(uf)

for d in range(1, st.session_state.trip_days_count + 1):
    if d not in st.session_state.trip_data: st.session_state.trip_data[d] = []

# Tabs
t1, t2, t3, t4, t5, t6 = st.tabs(["📅 行程", "🗺️ 地圖", "✨ 願望", "🎒 清單", "ℹ️ 資訊", "🧰 工具"])

# --- Tab 1: 行程 ---
with t1:
    day = st.radio("Day", list(range(1, st.session_state.trip_days_count + 1)), horizontal=True, label_visibility="collapsed", format_func=lambda x: f"D{x}")
    curr_d = st.session_state.start_date + timedelta(days=day-1)
    items = st.session_state.trip_data[day]
    items.sort(key=lambda x: x['time'])
    
    # 預算
    tc = sum([it['cost'] for it in items])
    ta = sum([sum(x['price'] for x in it.get('expenses', [])) for it in items])
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("預算", f"¥{tc:,}")
    c_m2.metric("支出", f"¥{ta:,}", delta=f"{tc-ta:,}" if ta>0 else None)
    if tc > 0 and ta > 0: st.progress(min(ta/tc, 1.0))

    # 天氣
    floc = items[0]['loc'] if items and items[0]['loc'] else "City"
    w = Weather.get(floc, curr_d)
    st.markdown(f"""<div class="weather-box"><div><div style="font-size:2rem;">{w['icon']}</div><div>{w['high']}° / {w['low']}°</div></div><div style="text-align:right;"><b>{curr_d.strftime('%m/%d')}</b><br>📍 {floc}<br>{w['desc']}</div></div>""", unsafe_allow_html=True)

    is_edit = st.toggle("編輯模式 (含收據)")
    if is_edit and st.button("➕ 新增"):
        st.session_state.trip_data[day].append({"id": int(time.time()*1000), "time": "09:00", "title": "新行程", "loc": "", "cost": 0, "note": "", "expenses": [], "trans_mode": "📍", "trans_min": 30})
        st.rerun()

    if not items: st.info("尚無行程")

    for i, item in enumerate(items):
        # 卡片
        mlink = item['loc'] if item['loc'].startswith("http") else f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(item['loc'])}"
        mbtn = f'<a href="{mlink}" target="_blank" style="text-decoration:none;margin-left:5px;font-size:0.8rem;">🗺️</a>' if item['loc'] else ""
        cost_tg = f'<span style="background:{cur["primary"]};color:white;padding:2px 6px;border-radius:8px;font-size:0.7rem;">¥{item["cost"]:,}</span>' if item['cost']>0 else ""
        
        exp_htm = ""
        if item.get('expenses'):
            rows = "".join([f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#666;'><span>{e['name']}</span><span>¥{e['price']:,}</span></div>" for e in item['expenses']])
            exp_htm = f"<div style='margin-top:5px;padding-top:5px;border-top:1px dashed #DDD;'>{rows}</div>"

        st.markdown(f"""<div style="display:flex;gap:10px;margin-bottom:0px;"><div style="width:50px;text-align:center;font-weight:bold;">{item['time']}<br><div style="height:100%;width:2px;background:{cur['secondary']};margin:0 auto;"></div></div><div style="flex:1;"><div class="apple-card"><div style="display:flex;justify-content:space-between;"><b>{item['title']}</b>{cost_tg}</div><div style="font-size:0.85rem;color:#666;">📍 {item['loc']}{mbtn}</div><div style="font-size:0.85rem;background:{cur['bg']};padding:5px;margin-top:5px;border-radius:5px;">📝 {item['note']}</div>{exp_htm}</div></div></div>""", unsafe_allow_html=True)

        if is_edit:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                item['title'] = c1.text_input("名", item['title'], key=f"t_{item['id']}")
                item['time'] = c2.text_input("時", item['time'], key=f"tm_{item['id']}")
                item['loc'] = st.text_input("地", item['loc'], key=f"l_{item['id']}")
                item['cost'] = st.number_input("算", value=item['cost'], step=100, key=f"c_{item['id']}")
                item['note'] = st.text_area("註", item['note'], key=f"n_{item['id']}")
                
                st.caption("📷 收據")
                cam = st.toggle("相機", key=f"tg_{item['id']}")
                if cam: ufile = st.camera_input("拍", key=f"cm_{item['id']}", label_visibility="collapsed")
                else: ufile = st.file_uploader("傳", type=["jpg","png"], key=f"up_{item['id']}", label_visibility="collapsed")
                
                fk = f"scan_ok_{item['id']}"
                if ufile and not st.session_state.get(fk, False):
                    with st.spinner("分析中..."):
                        res = analyze_receipt_image(ufile)
                    cnt = 0
                    for r in res:
                        if r['price']>0: 
                            item['expenses'].append(r)
                            cnt+=1
                    if cnt>0:
                        item['cost'] = sum(x['price'] for x in item['expenses'])
                        st.success(f"加入 {cnt} 筆")
                        st.session_state[fk] = True
                        time.sleep(1)
                        st.rerun()
                if not ufile: st.session_state[fk] = False

                cx1, cx2, cx3 = st.columns([2,1,1])
                n = cx1.text_input("項", key=f"nn_{item['id']}")
                p = cx2.number_input("金", min_value=0, key=f"np_{item['id']}")
                if cx3.button("➕", key=f"bt_{item['id']}"):
                     if n and p>0:
                        item['expenses'].append({"name":n, "price":p})
                        item['cost'] = sum(x['price'] for x in item['expenses'])
                        st.rerun()
                
                if item.get('expenses'):
                    with st.expander("細項"):
                        for idx, e in enumerate(item['expenses']):
                            c_d1, c_d2 = st.columns([4,1])
                            c_d1.text(f"{e['name']} {e['price']}")
                            if c_d2.button("X", key=f"dx_{item['id']}_{idx}"):
                                item['expenses'].pop(idx)
                                st.rerun()
                if st.button("🗑️ 刪除", key=f"rm_{item['id']}"):
                    st.session_state.trip_data[day].pop(i)
                    st.rerun()

        # 交通
        if i < len(items)-1:
            nxt = items[i+1]
            turl = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(item['loc'])}&destination={urllib.parse.quote(nxt['loc'])}&travelmode=transit"
            if is_edit:
                ct1, ct2 = st.columns([1,1])
                item['trans_mode'] = ct1.selectbox("法", TRANSPORT_OPTIONS, key=f"tr_{item['id']}")
                item['trans_min'] = ct2.number_input("分", value=item.get('trans_min',30), step=5, key=f"trm_{item['id']}")
            else:
                st.markdown(f"""<div style="display:flex;gap:10px;"><div style="width:50px;text-align:center;"><div style="height:100%;width:2px;border-left:2px dashed {cur['secondary']};margin:0 auto;"></div></div><div style="flex:1;padding:5px 0;"><div class="trans-box"><div style="font-size:0.8rem;color:#888;">推薦路線</div><div style="font-weight:bold;">{item.get('trans_mode','📍')}</div><div style="font-size:0.8rem;">{item.get('trans_min',30)} min <a href="{turl}" target="_blank">➤</a></div></div></div></div>""", unsafe_allow_html=True)

# --- Tab 2: 地圖 ---
with t2:
    m_list = sorted(st.session_state.trip_data[day], key=lambda x: x['time'])
    valid = [i for i in m_list if i['loc']]
    gurl = f"https://www.google.com/maps/dir/{'/'.join([urllib.parse.quote(i['loc']) for i in valid])}" if valid else "#"
    st.markdown(f"<div style='text-align:center;margin-bottom:10px;'><a href='{gurl}' target='_blank' style='background:{cur['primary']};color:white;padding:10px 20px;border-radius:20px;text-decoration:none;'>Google Maps 導航</a></div>", unsafe_allow_html=True)
    
    if MAP_AVAILABLE and valid:
        start = get_lat_lon(valid[0]['loc']) or [35.6895, 139.6917]
        m = folium.Map(location=start, zoom_start=13)
        pts = []
        for idx, x in enumerate(valid):
            c = get_lat_lon(x['loc'])
            if c:
                pts.append(c)
                folium.Marker(c, popup=x['title'], icon=folium.Icon(color='red', icon=str(idx+1), prefix='fa')).add_to(m)
        if len(pts)>1: folium.PolyLine(pts, color="blue", weight=5).add_to(m)
        st_folium(m, width="100%", height=400)
    else: st.info("無地圖資料或模組")

# --- Tab 3: 願望 ---
with t3:
    with st.expander("➕ 新增"):
        wt = st.text_input("名")
        wl = st.text_input("地")
        wn = st.text_input("註")
        if st.button("加") and wt:
            st.session_state.wishlist.append({"id":int(time.time()), "title":wt, "loc":wl, "note":wn})
            st.rerun()
    for i, w in enumerate(st.session_state.wishlist):
        st.markdown(f"""<div class="apple-card" style="border-left:4px solid {cur['primary']};"><b>{w['title']}</b><br><span style="font-size:0.8rem;">{w['loc']} {w['note']}</span></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns([2,1])
        td = c1.selectbox("移至", list(range(1, st.session_state.trip_days_count+1)), key=f"wd_{w['id']}")
        if c2.button("排", key=f"wm_{w['id']}"):
            st.session_state.trip_data[td].append({"id":int(time.time()), "time":"09:00", "title":w['title'], "loc":w['loc'], "cost":0, "note":w['note'], "expenses":[], "cat":"spot"})
            st.session_state.wishlist.pop(i)
            st.rerun()

# --- Tab 4: 清單 ---
with t4:
    st.info("建議："+", ".join(get_packing(st.session_state.trip_data, st.session_state.start_date)))
    for c, its in st.session_state.checklist.items():
        st.markdown(f"**{c}**")
        cols = st.columns(2)
        for idx, (k,v) in enumerate(its.items()):
            st.session_state.checklist[c][k] = cols[idx%2].checkbox(k, value=v)

# --- Tab 5: 資訊 ---
with t5:
    f = st.session_state.flight_info
    st.markdown(f"""<div class="info-card"><b>航班</b><br>去 {f['out']['date']} {f['out']['code']}<br>回 {f['in']['date']} {f['in']['code']}</div>""", unsafe_allow_html=True)
    
    edi = st.toggle("編輯")
    if edi and st.button("加飯店"): st.session_state.hotel_info.append({"id":int(time.time()),"name":"新飯店","addr":""})
    
    for i, h in enumerate(st.session_state.hotel_info):
        if edi:
            h['name'] = st.text_input("名", h['name'], key=f"hn_{i}")
            h['addr'] = st.text_input("址", h.get('addr',''), key=f"ha_{i}")
        lnk = h.get('addr','') if h.get('addr','').startswith("http") else f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(h.get('name',''))}"
        st.markdown(f"""<div class="info-card" style="border-left:4px solid {cur['primary']};"><b>{h['name']}</b><br>📍 {h.get('addr','')} <a href="{lnk}">Map</a></div>""", unsafe_allow_html=True)

# --- Tab 6: 工具 ---
with t6:
    c1, c2 = st.columns(2)
    if c1.button("☁️ 上傳"):
        if CLOUD_AVAILABLE:
            res = cloud_save({"trip":st.session_state.trip_data, "wish":st.session_state.wishlist})
            st.toast(res[1])
        else: st.error("無雲端")
    if c2.button("📥 下載"):
        if CLOUD_AVAILABLE:
            raw = cloud_load()
            if raw:
                d = json.loads(raw)
                if "trip" in d: st.session_state.trip_data = {int(k):v for k,v in d['trip'].items()}
                st.toast("OK")
                time.sleep(1)
                st.rerun()
    
    st.divider()
    amt = st.number_input("匯率", step=100)
    st.metric("NT$", int(amt * st.session_state.exchange_rate))
    
    st.divider()
    tc = st.session_state.target_country
    if tc in PHRASES:
        typ = st.selectbox("情境", list(PHRASES[tc].keys()))
        for p in PHRASES[tc][typ]:
            st.markdown(f"<div class='apple-card' style='padding:10px;margin-bottom:5px;'>{p[0]}<br><b>{p[1]}</b></div>", unsafe_allow_html=True)
