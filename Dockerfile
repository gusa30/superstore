FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- workdir ----
WORKDIR /app

# ---- 安裝套件（利用快取）----
COPY requirements.txt .
RUN pip install --upgrade pip &&     pip install --no-cache-dir -r requirements.txt

# ---- 複製專案檔 ----
COPY . .

# ---- Cloud Run 會注入 $PORT ----
ENV PORT=8080

# ---- 啟動 Streamlit ----
CMD ["bash", "-lc", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]
