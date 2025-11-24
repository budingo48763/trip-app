    /* 全局字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700;900&display=swap');
    
    .stApp { 
        background-color: #FDFCF5 !important; /* 米色紙張感 */
        color: #2B2B2B !important; 
        font-family: 'Noto Serif JP', 'Times New Roman', serif !important;
    }
    
    /* === 修正部分開始 === */
    /* 只隱藏 Deploy 按鈕，保留 Header 以便手機版能點擊側邊欄開關 */
    .stDeployButton {visibility: hidden;}
    
    /* 讓頂部 Header 背景透明，融入頁面 */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    /* === 修正部分結束 === */

    /* =========================================
       1. 側邊欄導航
       ========================================= */