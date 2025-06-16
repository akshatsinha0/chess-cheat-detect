FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 1. Copy Stockfish executable to a non-conflicting path
COPY bin/stockfish/stockfish-windows-x86-64-avx2.exe /app/engine/stockfish
RUN chmod +x /app/engine/stockfish

# 2. Copy remaining source code
COPY . .

# CMD to run the application
CMD ["python", "main.py"]
