import streamlit as st
import pandas as pd
import joblib
import numpy as np
import sqlite3
from datetime import datetime

# --- SQLite 連線 ---
conn = sqlite3.connect('predictions.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS customer_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    Year_Birth INTEGER,
    Education TEXT,
    Marital_Status TEXT,
    Income REAL,
    Kidhome INTEGER,
    Teenhome INTEGER,
    Recency INTEGER,
    MntWines REAL,
    MntMeatProducts REAL,
    MntSweetProducts REAL,
    NumDealsPurchases INTEGER,
    NumWebPurchases INTEGER,
    NumCatalogPurchases INTEGER,
    NumStorePurchases INTEGER,
    NumWebVisitsMonth INTEGER,
    Customer_Days INTEGER,
    TotalSpend REAL,
    log_MntWines REAL,
    log_MntMeatProducts REAL,
    log_MntSweetProducts REAL,
    log_TotalSpend REAL,
    log_Income REAL,
    Prediction INTEGER,
    Prediction_Prob REAL
)
""")
conn.commit()

st.title("💡 客戶活動參與預測器")
st.subheader("請輸入客戶資訊以預測其參與活動的可能性。")

# --- 模型與欄位載入 ---
try:
    pipeline = joblib.load("et_k16_tuned_pipeline.pkl")
    selected_raw_cols = [
        "Year_Birth", "Education", "Marital_Status", "Income",
        "Kidhome", "Teenhome", "Recency",
        "MntWines", "MntMeatProducts", "MntSweetProducts",
        "NumDealsPurchases", "NumWebPurchases", "NumCatalogPurchases",
        "NumStorePurchases", "NumWebVisitsMonth",
        "Customer_Days", "TotalSpend",
        "log_MntWines", "log_MntMeatProducts", "log_MntSweetProducts",
        "log_TotalSpend", "log_Income"
    ]
    st.success("✅ 模型與欄位清單已成功載入！")
except Exception as e:
    st.error(f"❌ 載入模型或欄位失敗：{e}")
    st.stop()

# --- 使用者輸入 ---
st.header("客戶基本資料")
col1, col2 = st.columns(2)

with col1:
    year_birth = st.number_input("出生年份", 1900, 2025, 1985)
    education = st.selectbox("教育程度", ["Basic", "Graduation", "Master", "PhD", "2n Cycle"])
    marital = st.selectbox("婚姻狀態", ["Single", "Together", "Married", "Divorced", "Widow", "Alone", "Absurd", "YOLO"])
    kidhome = st.number_input("家中幼兒人數", 0, 10, 0)
    teenhome = st.number_input("家中青少年人數", 0, 10, 0)

with col2:
    income = st.number_input("年收入", 0, step=1)
    recency = st.number_input("最近購買天數", 0, 9999, 0)
    customer_days = st.number_input("成為會員天數", 0, 9999, 0)

st.header("客戶消費金額")
total_spend = st.number_input("總消費金額", 0, step=1)
col3, col4, col5 = st.columns(3)

with col3:
    wines_pct = st.number_input("葡萄酒 (%)", 0, 100, 0)

with col4:
    meat_pct = st.number_input("肉品 (%)", 0, 100, 0)

with col5:
    sweet_pct = st.number_input("甜食 (%)", 0, 100, 0)

st.header("客戶購買行為")
col6, col7 = st.columns(2)
with col6:
    NumWebPurchases = st.number_input("網路購買次數", 0, step=1)
    NumCatalogPurchases = st.number_input("目錄購買次數", 0, step=1)
    NumStorePurchases = st.number_input("實體店面購買次數", 0, step=1)

with col7:
    NumDealsPurchases = st.number_input("優惠/促銷購買次數", 0, step=1)
    NumWebVisitsMonth = st.number_input("每月網路瀏覽次數", 0, step=1)


# --- 預測 ---
if st.button("點此預測"):
    total_pct = wines_pct + meat_pct + sweet_pct

    mnt_wines = (wines_pct/100)*total_spend
    mnt_meat = (meat_pct/100)*total_spend
    mnt_sweet = (sweet_pct/100)*total_spend

    input_data = pd.DataFrame([{
        "Year_Birth": year_birth,
        "Education": education,
        "Marital_Status": marital,
        "Income": float(income),
        "Kidhome": kidhome,
        "Teenhome": teenhome,
        "Recency": recency,
        "MntWines": mnt_wines,
        "MntMeatProducts": mnt_meat,
        "MntSweetProducts": mnt_sweet,
        "NumDealsPurchases": NumDealsPurchases,
        "NumWebPurchases": NumWebPurchases,
        "NumCatalogPurchases": NumCatalogPurchases,
        "NumStorePurchases": NumStorePurchases,
        "NumWebVisitsMonth": NumWebVisitsMonth,
        "Customer_Days": customer_days,
        "TotalSpend": total_spend,
        "log_MntWines": np.log1p(mnt_wines),
        "log_MntMeatProducts": np.log1p(mnt_meat),
        "log_MntSweetProducts": np.log1p(mnt_sweet),
        "log_TotalSpend": np.log1p(total_spend),
        "log_Income": np.log1p(float(income))
    }])

    # 補齊缺少欄位
    for col in selected_raw_cols:
        if col not in input_data.columns:
            input_data[col] = 0
    input_data = input_data[selected_raw_cols]

    try:
        prob = pipeline.predict_proba(input_data)[0, 1]
        pred = int(prob >= 0.305)
        if pred==1:
            st.success(f"🎉 該客戶很可能會參加活動！（機率 {prob:.2%}）")
        else:
            st.info(f"🤔 該客戶可能不會參加活動。（機率 {prob:.2%}）")

        record = input_data.iloc[0].to_dict()
        record.update({
            "Prediction": pred,
            "Prediction_Prob": float(prob),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        placeholders = ', '.join(['?']*len(record))
        columns = ', '.join(record.keys())
        sql = f"INSERT INTO customer_predictions ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(record.values()))
        conn.commit()
        st.success("✅ 資料已成功儲存！")
    except Exception as e:
        st.error(f"❌ 預測失敗：{e}")
